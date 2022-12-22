import pandas as pd
import numpy as np
import sqlite3 as sq
import json
import re
import glob
import qbstreamlit.data
import streamlit as st

def parse_stats(qbj, player_recoding, team_recoding):
    team_dict = {}
    for i, row in team_recoding.iterrows():
        team_dict[row['team']] = row['team_clean']
    player_dict = {}
    for i, row in player_recoding.iterrows():
        player_dict[f"{row['player']}-{row['team']}"] = row['player_clean']

    match_players = []
    for team in qbj['match_teams']:
        for lineup in team['lineups']:
            match_players.extend(
                [{'name': player['name'], 'team': team['team']['name']} for player in lineup['players']])

    buzzes = []
    for question in qbj['match_questions']:
        for buzz in question['buzzes']:
            buzzes.append(
                {
                    'tossup': question['question_number'],
                    'player': player_dict[f"{buzz['player']['name']}-{team_dict[buzz['team']['name']]}"],
                    'team': team_dict[buzz['team']['name']],
                    'buzz_position': buzz['buzz_position']['word_index'],
                    'value': str(buzz['result']['value'])
                }
            )
    player_stats = pd.DataFrame(buzzes).groupby(
        ['player', 'team', 'value'], as_index=False
    ).agg('size').pivot(
        index=['player', 'team'], columns='value', values='size'
    ).reset_index()

    for x in ['15', '10', '-5']:
        if x not in player_stats.columns:
            player_stats[x] = 0

    if '0' in player_stats.columns:
        player_stats = player_stats.drop(columns=['0'])

    for player in match_players:
        if player_dict[f"{player['name']}-{team_dict[player['team']]}"] not in player_stats['player'].values:
            player_stats.loc[len(player_stats.index)] = [
                player['name'], player['team'], 0, 0, 0]

    player_stats[['15', '10', '-5']
                 ] = player_stats[['15', '10', '-5']].fillna(0).astype(int)
    player_stats['Pts'] = 15*player_stats['15'] + \
        10*player_stats['10'] - 5*player_stats['-5']
    player_stats = player_stats[['player', 'team', '15', '10', '-5', 'Pts']]

    buzzes = pd.DataFrame(buzzes)

    all_bonuses = [{'bonus': question['bonus'], 'question_number': question['question_number']}
                   for question in qbj['match_questions'] if 'bonus' in question]
    bonus_df = []
    bonuses = []
    for bonus in all_bonuses:
        bonus_df.append(
            {
                'tossup': bonus['question_number'],
                'bonus': bonus['bonus']['question']['question_number'],
                'value': sum([part['controlled_points'] for part in bonus['bonus']['parts']])
            }
        )

        bonuses.append(
            {
                'tossup': bonus['question_number'],
                'bonus': bonus['bonus']['question']['question_number'],
                'part1_value': bonus['bonus']['parts'][0]['controlled_points'],
                'part2_value': bonus['bonus']['parts'][1]['controlled_points'],
                'part3_value': bonus['bonus']['parts'][2]['controlled_points']
            }
        )

    team_bonuses = pd.DataFrame(bonus_df).merge(buzzes[buzzes['value'].isin(['15', '10'])][['tossup', 'team']], on='tossup').groupby(['team'], as_index=False).agg(
        {'value': 'sum'}
    ).rename(columns={'value': 'BPts'})

    bonuses = pd.DataFrame(bonuses).merge(
        buzzes[buzzes['value'].isin(['15', '10'])][['tossup', 'team']], on='tossup')

    team_stats = player_stats.groupby('team', as_index=False).agg(
        'sum').rename(columns={'Pts': 'TUPts'})
    team_stats['BHrd'] = team_stats['10']
    team_stats = team_stats.merge(pd.DataFrame(team_bonuses))
    team_stats['PPB'] = team_stats['BPts']/team_stats['BHrd']
    team_stats['PPB'] = team_stats['PPB'].round(decimals=2)
    team_stats['Pts'] = team_stats['TUPts'] + team_stats['BPts']

    for team in qbj['match_teams']:
        if team_dict[team['team']['name']] not in team_stats['team'].values:
            team_stats.loc[len(team_stats.index)] = [
                team_dict[team['team']['name']], 0, 0, 0, 0, 0, 0, 0.00, 0]

    return buzzes, bonuses, player_stats, team_stats


def parse_packet(packet):
    tossup_meta = []
    for i in range(len(packet['tossups'])):
        if 'metadata' in packet['tossups'][i]:
            tossup_meta.append(
                {
                    'tossup': i + 1,
                    'answer': packet['tossups'][i]['answer'],
                    'author': packet['tossups'][i]['metadata'].split(', ')[0],
                    'category': packet['tossups'][i]['metadata'].split(', ')[1]
                }
            )
        else:
            tossup_meta.append(
                {
                    'tossup': i + 1,
                    'answer': packet['tossups'][i]['answer'],
                    'category': packet['tossups'][i]['category'],
                    'subcategory': packet['tossups'][i]['subcategory']
                }
            )

    tossup_meta = pd.DataFrame(tossup_meta)

    bonus_meta = []
    for i in range(len(packet['bonuses'])):
        if 'metadata' in packet['bonuses'][i]:
            bonus_meta.append(
                {
                    'bonus': i + 1,
                    'answers': ' / '.join(packet['bonuses'][i]['answers_sanitized']),
                    'author': packet['bonuses'][i]['metadata'].split(', ')[0],
                    'category': packet['bonuses'][i]['metadata'].split(', ')[1]
                }
            )
        else:
            bonus_meta.append(
                {
                    'bonus': i + 1,
                    'answers': ' / '.join(packet['bonuses'][i]['answers']),
                    'category': packet['bonuses'][i]['category'],
                    'subcategory': packet['bonuses'][i]['subcategory']
                }
            )

    bonus_meta = pd.DataFrame(bonus_meta)

    return tossup_meta, bonus_meta


def populate_db_qbjs(qbjs):
    all_buzzes = []
    all_bonuses = []
    all_player_stats = []
    all_team_stats = []

    for i, qbj_path in enumerate(qbjs):
        qbj = json.load(qbj_path)

        packet = re.search(r'(?<=Round\s)\d+', qbj_path.name).group(0)
        buzzes, bonuses, player_stats, team_stats = parse_stats(qbj)

        buzzes['packet'] = packet
        buzzes['game_id'] = i
        bonuses['packet'] = packet
        bonuses['game_id'] = i
        player_stats['packet'] = packet
        player_stats['game_id'] = i
        team_stats['packet'] = packet
        team_stats['game_id'] = i

        all_buzzes.append(buzzes)
        all_bonuses.append(bonuses)
        all_player_stats.append(player_stats)
        all_team_stats.append(team_stats)

    player_bpas, player_cat_bpas = calculate_player_bpas(
        pd.concat(all_buzzes), pd.concat(all_player_stats))
    team_bpas, team_cat_bpas = calculate_team_bpas(
        pd.concat(all_buzzes), pd.concat(all_player_stats))

    con = sq.connect('stats.db')

    pd.concat(all_buzzes).to_sql(name='buzzes', con=con, if_exists='replace')
    pd.concat(all_bonuses).to_sql(name='bonuses', con=con, if_exists='replace')
    pd.concat(all_player_stats).to_sql(
        name='player_stats', con=con, if_exists='replace')
    pd.concat(all_team_stats).to_sql(
        name='team_stats', con=con, if_exists='replace')

    player_bpas.to_sql(name='player_bpa', con=con, if_exists='replace')
    player_cat_bpas.to_sql(name='player_cat_bpa', con=con, if_exists='replace')
    team_bpas.to_sql(name='team_bpa', con=con, if_exists='replace')
    team_cat_bpas.to_sql(name='team_cat_bpa', con=con, if_exists='replace')


def populate_db_qbjs_nasat(tournament):
    all_buzzes = []
    all_bonuses = []
    all_player_stats = []
    all_team_stats = []

    player_recoding = pd.read_csv('player-recoding.csv')
    team_recoding = pd.read_csv('team-recoding.csv')

    for i, qbj_path in enumerate(glob.glob(f'qbjs/{st.session_state.tournament}/*.qbj')):
        with open(qbj_path, 'r') as f:
            qbj = json.load(f)
        
        print(i)

        if 'round-recoding.json' in glob.glob('*'):
            with open('round-recoding.json', 'r') as f:
                round_recoding = json.load(f)
            packet = round_recoding[st.session_state.tournament][qbj_path[5:]]
        else:
            packet = re.search(r'(?<=Round_)\d+', qbj_path).group(0)
        buzzes, bonuses, player_stats, team_stats = parse_stats(
            qbj,
            player_recoding,
            team_recoding
        )

        buzzes['packet'] = packet
        buzzes['game_id'] = i
        bonuses['packet'] = packet
        bonuses['game_id'] = i
        player_stats['packet'] = packet
        player_stats['game_id'] = i
        team_stats['packet'] = packet
        team_stats['game_id'] = i

        if i == 128:
            print(player_stats)

        all_buzzes.append(buzzes)
        all_bonuses.append(bonuses)
        all_player_stats.append(player_stats)
        all_team_stats.append(team_stats)

    player_bpas, player_cat_bpas = calculate_player_bpas(
        tournament, pd.concat(all_buzzes), pd.concat(all_player_stats))
    team_bpas, team_cat_bpas = calculate_team_bpas(
        tournament, pd.concat(all_buzzes), pd.concat(all_player_stats))

    con = sq.connect('stats.db')

    pd.concat(all_buzzes).to_sql(name='buzzes', con=con, if_exists='replace')
    pd.concat(all_bonuses).to_sql(name='bonuses', con=con, if_exists='replace')
    pd.concat(all_player_stats).to_sql(
        name='player_stats', con=con, if_exists='replace')
    pd.concat(all_team_stats).to_sql(
        name='team_stats', con=con, if_exists='replace')

    player_bpas.to_sql(name='player_bpa', con=con, if_exists='replace')
    player_cat_bpas.to_sql(name='player_cat_bpa', con=con, if_exists='replace')
    team_bpas.to_sql(name='team_bpa', con=con, if_exists='replace')
    team_cat_bpas.to_sql(name='team_cat_bpa', con=con, if_exists='replace')


def populate_db_packets(packets):
    all_tossup_meta = []
    all_bonus_meta = []
    for packet_path in packets:
        packet = json.load(packet_path)
        packet_num = re.search(r'(?<=packet)\d+', packet_path.name).group(0)

        json_object = json.dumps(packet)

        with open(f"packets/packet{packet_num}.json", "w") as outfile:
            outfile.write(json_object)

        tossup_meta, bonus_meta = parse_packet(packet)
        tossup_meta['packet'] = packet_num
        bonus_meta['packet'] = packet_num
        all_tossup_meta.append(tossup_meta)
        all_bonus_meta.append(bonus_meta)

    con = sq.connect('stats.db')

    pd.concat(all_tossup_meta).to_sql(
        name='tossup_meta', con=con, if_exists='replace')
    pd.concat(all_bonus_meta).to_sql(
        name='bonus_meta', con=con, if_exists='replace')


def populate_db_packets_nasat(tournament):
    all_tossup_meta = []
    all_bonus_meta = []
    for packet_path in glob.glob(f'packets/{tournament}/*.json'):
        with open(packet_path, "r") as f:
            packet = json.load(f)

        packet_num = re.search(r'(?<=packet)\d+', packet_path).group(0)

        tossup_meta, bonus_meta = parse_packet(packet)

        tossup_meta['packet'] = packet_num
        bonus_meta['packet'] = packet_num
        all_tossup_meta.append(tossup_meta)
        all_bonus_meta.append(bonus_meta)

    con = sq.connect('stats.db')

    pd.concat(all_tossup_meta).to_sql(
        name='tossup_meta', con=con, if_exists='replace')
    pd.concat(all_bonus_meta).to_sql(
        name='bonus_meta', con=con, if_exists='replace')


def calculate_bpa(buzzes, tuh):
    buzzes['bpa_comp'] = buzzes['celerity']*100/tuh
    return (sum(buzzes['bpa_comp']))


def calculate_player_bpas(tournament, buzzes, player_stats):
    tossup_meta = qbstreamlit.data.load_tossup_meta()
    packet_meta = qbstreamlit.data.get_packet_meta(tournament)

    buzzes['packet'] = buzzes['packet'].astype(int)

    full_buzzes = buzzes.merge(
        tossup_meta, on=['packet', 'tossup']
    ).merge(
        packet_meta, on=['packet', 'tossup']
    )

    full_buzzes['celerity'] = 1 - full_buzzes['buzz_position'] / \
        full_buzzes['tossup_length']

    player_games = player_stats.groupby(
        ['player', 'team']
    ).agg({'game_id': 'nunique'}).reset_index().rename(columns={'game_id': 'Games'})
    player_games['TUH'] = player_games['Games']*20

    player_bpa_list = []
    for i, row in player_games.iterrows():
        player_buzzes = full_buzzes[full_buzzes['value'].isin(['15', '10'])]
        player_buzzes = player_buzzes[player_buzzes['player'] == row['player']]
        player_buzzes = player_buzzes[player_buzzes['team'] == row['team']]

        player_bpa_list.append({
            'player': row['player'],
            'team': row['team'],
            'BPA': calculate_bpa(player_buzzes, row['TUH']),
            'ACC': np.mean(player_buzzes['celerity'])
        })
    player_bpa = pd.DataFrame(player_bpa_list)

    packet_tuhs = {
        'History': 4,
        'Science': 4,
        'Literature': 4,
        'Arts': 3,
        'Beliefs': 2,
        'Thought': 2,
        'Other': 1,
    }

    player_cat_bpa_list = []
    for i, row in player_games.iterrows():
        for category, tuh in packet_tuhs.items():
            player_cat_buzzes = full_buzzes[full_buzzes['value'].isin([
                                                                      '15', '10'])]
            player_cat_buzzes = player_cat_buzzes[player_cat_buzzes['player']
                                                  == row['player']]
            player_cat_buzzes = player_cat_buzzes[player_cat_buzzes['team'] == row['team']]
            player_cat_buzzes = player_cat_buzzes[player_cat_buzzes['category'] == category]

            player_cat_bpa_list.append({
                'player': row['player'],
                'team': row['team'],
                'category': category,
                'BPA': calculate_bpa(player_cat_buzzes, row['Games']*tuh),
                'ACC': np.mean(player_cat_buzzes['celerity'])
            })
    player_cat_bpa = pd.DataFrame(player_cat_bpa_list)
    return player_bpa, player_cat_bpa


def calculate_team_bpas(tournament, buzzes, team_stats):
    tossup_meta = qbstreamlit.data.load_tossup_meta()
    packet_meta = qbstreamlit.data.get_packet_meta(tournament)

    buzzes['packet'] = buzzes['packet'].astype(int)

    full_buzzes = buzzes.merge(
        tossup_meta, on=['packet', 'tossup']
    ).merge(
        packet_meta, on=['packet', 'tossup']
    )
    full_buzzes['celerity'] = 1 - full_buzzes['buzz_position'] / \
        full_buzzes['tossup_length']

    team_games = team_stats.groupby(
        ['team']
    ).agg({'game_id': 'nunique'}).reset_index().rename(columns={'game_id': 'Games'})
    team_games['TUH'] = team_games['Games']*20

    team_bpa_list = []
    for i, row in team_games.iterrows():
        team_buzzes = full_buzzes[full_buzzes['value'].isin(['15', '10'])]
        team_buzzes = team_buzzes[team_buzzes['team'] == row['team']]
        team_bpa_list.append({
            'team': row['team'],
            'BPA': calculate_bpa(team_buzzes, row['TUH']),
            'ACC': np.mean(team_buzzes['celerity'])
        })
    team_bpa = pd.DataFrame(team_bpa_list)

    packet_tuhs = {
        'History': 4,
        'Science': 4,
        'Literature': 4,
        'Arts': 3,
        'Beliefs': 2,
        'Thought': 2,
        'Other': 1,
    }

    team_cat_bpa_list = []
    for i, row in team_games.iterrows():
        for category, tuh in packet_tuhs.items():
            team_cat_buzzes = full_buzzes[full_buzzes['value'].isin([
                                                                    '15', '10'])]
            team_cat_buzzes = team_cat_buzzes[team_cat_buzzes['team']
                                              == row['team']]
            team_cat_buzzes = team_cat_buzzes[team_cat_buzzes['category'] == category]
            team_cat_bpa_list.append({
                'team': row['team'],
                'category': category,
                'BPA': calculate_bpa(team_cat_buzzes, row['Games']*tuh),
                'ACC': np.mean(team_cat_buzzes['celerity'])
            })
    team_cat_bpa = pd.DataFrame(team_cat_bpa_list)

    return team_bpa, team_cat_bpa
