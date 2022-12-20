import sqlite3 as sq
import pandas as pd
import glob
import json
import streamlit as st

def fetch_df(_cursor):
    rows = _cursor.fetchall()
    keys = [k[0] for k in _cursor.description]
    game_results = [dict(zip(keys, row)) for row in rows]
    results = pd.DataFrame(game_results)
    return results

def load_buzzes():
    con = sq.connect('stats.db')
    cur = con.cursor()

    cur.execute('SELECT * FROM buzzes')
    buzzes = fetch_df(cur)
    con.close()
    buzzes[['packet']] = buzzes[['packet']].astype(int)
    buzzes[['tossup']] = buzzes[['tossup']].astype(int)
    buzzes[['buzz_position']] = buzzes[['buzz_position']].astype(int)
    buzzes[['value']] = buzzes[['value']].astype(int)
    return buzzes

def load_bonuses():
    con = sq.connect('stats.db')
    cur = con.cursor()

    cur.execute('SELECT * FROM bonuses')
    bonuses = fetch_df(cur)
    con.close()
    bonuses[['packet']] = bonuses[['packet']].astype(int)
    bonuses[['bonus']] = bonuses[['bonus']].astype(int)
    bonuses[['tossup']] = bonuses[['tossup']].astype(int)
    return bonuses

def load_tossup_meta():
    con = sq.connect('stats.db')
    cur = con.cursor()

    cur.execute('SELECT * FROM tossup_meta')
    tossup_meta = fetch_df(cur)
    con.close()
    tossup_meta[['packet']] = tossup_meta[['packet']].astype(int)
    return tossup_meta

def load_bonus_meta():
    con = sq.connect('stats.db')
    cur = con.cursor()

    cur.execute('SELECT * FROM bonus_meta')
    bonus_meta = fetch_df(cur)
    con.close()
    bonus_meta[['packet']] = bonus_meta[['packet']].astype(int)
    return bonus_meta

def load_team_stats():
    con = sq.connect('stats.db')
    cur = con.cursor()

    cur.execute('SELECT * FROM team_stats')
    team_stats = fetch_df(cur)
    con.close()
    return team_stats

def load_player_stats():
    con = sq.connect('stats.db')
    cur = con.cursor()

    cur.execute('SELECT * FROM player_stats')
    player_stats = fetch_df(cur)
    con.close()
    return player_stats

def load_player_bpa():
    con = sq.connect('stats.db')
    cur = con.cursor()

    cur.execute('SELECT * FROM player_bpa')
    player_bpa = fetch_df(cur)
    cur.execute('SELECT * FROM player_cat_bpa')
    player_cat_bpa = fetch_df(cur)
    con.close()
    return player_bpa, player_cat_bpa

def load_team_bpa():
    con = sq.connect('stats.db')
    cur = con.cursor()

    cur.execute('SELECT * FROM team_bpa')
    team_bpa = fetch_df(cur)
    cur.execute('SELECT * FROM team_cat_bpa')
    team_cat_bpa = fetch_df(cur)
    con.close()
    return team_bpa, team_cat_bpa

def get_packets(tournament):
    packets = {}
    for file in glob.glob(f'packets/{tournament}/*.json'):
        print(file)
        with open(file, 'r') as f:
            packets[file] = json.load(f)
    return packets

def get_packet_meta(tournament):
    packets = get_packets(tournament)
    packet_meta = []
    for packet in packets.keys():
        for tossup in packets[packet]['tossups']:
            packet_meta.append(
                {
                    'packet': tossup['packetNumber'],
                    'tossup': tossup['questionNumber'],
                    'tossup_length': len(tossup['question'].split(' '))
                }
            )
    return pd.DataFrame(packet_meta)