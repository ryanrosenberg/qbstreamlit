import altair as alt
import numpy as np
import pandas as pd
import qbstreamlit.utils
from textwrap import wrap


def make_buzz_chart(df):
    c = alt.Chart(df).mark_square(size=100).encode(x='buzz_position', y=alt.Y(field='num', type='ordinal',
                                                                              sort='descending'), color=alt.Color('team', legend=None), tooltip=['player', 'team', 'buzz_position', 'answer'])
    return c


def make_category_buzz_chart(df, negs):
    df['category'] = ['Other' if cat in ['Geo/CE', 'Other Academic']
                      else cat for cat in df['category']]
    if not negs:
        df = df[df['value'].isin([15, 10])]
    else:
        df = df[df['value'].isin([15, 10, -5])]

    domain = [15, 10, -5]
    range_ = ['blue', '#007ccf', '#ff4b4b']

    c = alt.Chart(df).mark_bar(
        opacity=0.8,
        binSpacing=2
    ).encode(
        x=alt.X('buzz_position', bin=alt.Bin(maxbins=10),
                scale=alt.Scale(domain=(0, 150))),
        y=alt.Y('count()'),
        color=alt.Color('value:O', scale=alt.Scale(
            domain=domain, range=range_)),
        facet=alt.Facet('category', columns=2)
    ).properties(
        width=200,
        height=150,
    )
    return c


def make_category_ppb_chart(df, cat_ppb):
    cat_ppb['rank'] = cat_ppb.groupby('category')['PPB'].rank(
        'min', ascending=False).astype(int)
    top_ppb = cat_ppb[cat_ppb['rank'] == 1]
    cat_ppb['rank'] = ['#' + str(c) for c in cat_ppb['rank']]
    cat_ppb = cat_ppb[cat_ppb['team'] == df['team'].unique()[0]]

    bar = alt.Chart(df).mark_bar().encode(
        x='category',
        y=alt.Y('PPB', scale=alt.Scale(domain=[0, 30])),
        color=alt.Color('category', scale=alt.Scale(scheme='viridis'))
    ).properties(
        width=alt.Step(60),  # controls width of bar.
        height=350
    )

    top = alt.Chart(top_ppb).mark_bar(
        color='black',
        opacity=0.15,
        thickness=2,
        size=60 * 0.9,  # controls width of tick.
    ).encode(
        x='category',
        y='PPB'
    )

    ppb = alt.Chart(df).mark_text(
        color='black',
        size=14,
        dy=-3,
        baseline='bottom'
    ).encode(
        x='category',
        y='PPB',
        text='PPB'
    )

    rank = alt.Chart(cat_ppb).mark_text(
        color='white',
        fontWeight='bold',
        size=14,
        dy=5,
        baseline='top'
    ).encode(
        x='category',
        y='PPB',
        text='rank'
    )

    return bar + top + ppb + rank


def make_scoresheet(game_id, buzzes, bonuses, player_stats, has_bonuses=True):
    game_buzzes = buzzes[buzzes['game_id'] == game_id]
    game_buzzes['value'] = game_buzzes['value'].astype(int)
    game_buzzes['answer'] = [qbstreamlit.utils.sanitize_answer(
        answer) for answer in game_buzzes['answer']]

    if has_bonuses:
        game_bonuses = bonuses[bonuses['game_id'] == game_id]
        game_bonuses['answers'] = [[qbstreamlit.utils.sanitize_answer(
            part) for part in answer.split(' / ')] for answer in game_bonuses['answers']]
        game_bonuses['answers'] = [
            ' / '.join(answers) for answers in game_bonuses['answers']]

        team1_bonuses = game_bonuses[game_bonuses['team'] == team1_name]
        team2_bonuses = game_bonuses[game_bonuses['team'] == team2_name]

        team1_bonuses = team1_bonuses.melt(
            id_vars=['tossup', 'answers'],
            value_vars=['part1_value', 'part2_value', 'part3_value'],
            var_name='part', value_name='value'
        )

        team2_bonuses = team2_bonuses.melt(
            id_vars=['tossup', 'answers'],
            value_vars=['part1_value', 'part2_value', 'part3_value'],
            var_name='part', value_name='value'
        )

    team1_name = game_buzzes['team'].unique().tolist()[0]
    team2_name = game_buzzes['team'].unique().tolist()[1]

    team1_buzzes = game_buzzes[game_buzzes['team'] == team1_name]
    team2_buzzes = game_buzzes[game_buzzes['team'] == team2_name]

    team1_score = []
    team2_score = []
    rscore1 = 0
    rscore2 = 0
    for i in range(1, 21):
        if len(team1_buzzes[team1_buzzes['tossup'] == i]['value']) > 0:
            team1_tossup = sum(
                team1_buzzes[team1_buzzes['tossup'] == i]['value'].tolist())
            if has_bonuses:
                team1_bonus = sum(
                    team1_bonuses[team1_bonuses['tossup'] == i]['value'].tolist())
                team1_score.append(rscore1 + team1_tossup + team1_bonus)
                rscore1 = rscore1 + team1_tossup + team1_bonus
            else:
                team1_score.append(rscore1 + team1_tossup)
                rscore1 = rscore1 + team1_tossup
        else:
            team1_score.append(rscore1)

        if len(team2_buzzes[team2_buzzes['tossup'] == i]['value']) > 0:
            team2_tossup = sum(
                team2_buzzes[team2_buzzes['tossup'] == i]['value'].tolist())
            if has_bonuses:
                team2_bonus = sum(
                    team2_bonuses[team2_bonuses['tossup'] == i]['value'].tolist())
                team2_score.append(rscore2 + team2_tossup + team2_bonus)
                rscore2 = rscore2 + team2_tossup + team2_bonus
            else:
                team2_score.append(rscore2 + team2_tossup)
                rscore2 = rscore2 + team2_tossup
        else:
            team2_score.append(rscore2)

    team1_score_df = pd.DataFrame(
        {'tossup': list(range(1, 21)), 'score': team1_score, 'total': [1]*20})
    team2_score_df = pd.DataFrame(
        {'tossup': list(range(1, 21)), 'score': team2_score, 'total': [1]*20})

    all_player_cells = pd.DataFrame({
        'player': np.repeat(player_stats['player'].unique(), 20),
        'tossup': list(range(1, 21))*len(player_stats['player'].unique())
    })

    all_bonus_cells = pd.DataFrame({
        'part': np.repeat(['part1_value', 'part2_value', 'part3_value'], 20),
        'tossup': list(range(1, 21))*3
    })

    all_total_cells = pd.DataFrame({
        'total': np.repeat(1, 20),
        'tossup': list(range(1, 21))
    })

    t1_tossups = alt.Chart(team1_buzzes).mark_text(
    ).encode(
        x=alt.X(
            "player:N",
            axis=alt.Axis(orient='top', ticks=False, offset=5),
            scale=alt.Scale(
                domain=player_stats[player_stats['team'] == team1_name]['player'].unique()),
            title=None),
        y=alt.Y(
            'tossup:O',
            scale=alt.Scale(domain=list(range(1, 21))),
            axis=alt.Axis(
                orient='left', domain=False, ticks=False, tickCount=20, title=None, labelAlign='right', labelFontWeight='bold', labelAngle=0
            )),
        text='value:Q',
        tooltip=[alt.Tooltip('answer:N', title="Tossup answer"), alt.Tooltip('buzz_position:Q', title="Buzz location")])
    if has_bonuses:
        t1_bonuses = alt.Chart(team1_bonuses).mark_text().encode(
            x=alt.X(
                'part:N',
                axis=alt.Axis(orient='top', ticks=False, labels=False,
                              offset=5, title=wrap(team1_name, width=12))
            ),
            y=alt.Y(
                'tossup:O',
                scale=alt.Scale(domain=list(range(1, 21))),
                axis=None),
            text='value:Q',
            tooltip=[alt.Tooltip('answers:N', title="Bonus answers")])
    t1_score = alt.Chart(team1_score_df).mark_text().encode(
        x=alt.X('total:N', axis=alt.Axis(orient='top',
                ticks=False, labels=False, offset=5)),
        y=alt.Y(
            'tossup:O',
            scale=alt.Scale(domain=list(range(1, 21))),
            axis=None),
        text='score:Q')
    t2_tossups = alt.Chart(team2_buzzes).mark_text().encode(
        x=alt.X(
            "player:N",
            axis=alt.Axis(orient='top', ticks=False, offset=5),
            scale=alt.Scale(
                domain=player_stats[player_stats['team'] == team2_name]['player'].unique()),
            title=None),
        y=alt.Y(
            'tossup:O',
            scale=alt.Scale(domain=list(range(1, 21))),
            axis=alt.Axis(
                orient='left', grid=False, ticks=False, tickCount=20, title=None, labelAlign='right', labelFontWeight='bold', labelAngle=0
            )),
        text='value:Q',
        tooltip=[alt.Tooltip('answer:N', title="Tossup answer"), alt.Tooltip('buzz_position:Q', title="Buzz location")])
    if has_bonuses:
        t2_bonuses = alt.Chart(team2_bonuses).mark_text().encode(
            x=alt.X(
                'part:N',
                axis=alt.Axis(orient='top', ticks=False, labels=False,
                              offset=5, title=wrap(team2_name, width=12))
            ),
            y=alt.Y(
                'tossup:O',
                scale=alt.Scale(domain=list(range(1, 21))),
                axis=None),
            text='value:Q',
            tooltip=[alt.Tooltip('answers:N', title="Bonus answers")])
    t2_score = alt.Chart(team2_score_df).mark_text().encode(
        x=alt.X('total:N', axis=alt.Axis(orient='top',
                ticks=False, offset=5, labels=False)),
        y=alt.Y(
            'tossup:O',
            scale=alt.Scale(domain=list(range(1, 21))),
            axis=None),
        text='score:Q')

    player_grid = alt.Chart(all_player_cells).mark_rect(
        stroke='black', strokeWidth=.1, fill=None
    ).encode(
        x='player:N', y=alt.Y('tossup:O'), detail='count()'
    )

    if has_bonuses:
        bonus_grid = alt.Chart(all_bonus_cells).mark_rect(
            stroke='black', strokeWidth=.1, fill=None
        ).encode(
            x='part:N', y='tossup:O'
        )

    total_grid = alt.Chart(all_total_cells).mark_rect(
        stroke='black', strokeWidth=.1, fill=None
    ).encode(
        x='total:N', y='tossup:O'
    )

    if has_bonuses:
        final_chart = alt.hconcat(
            alt.hconcat(t1_tossups + player_grid, t1_bonuses +
                        bonus_grid, t1_score + total_grid, spacing=10),
            alt.hconcat(t2_tossups + player_grid, t2_bonuses +
                        bonus_grid, t2_score + total_grid, spacing=10),
            spacing=-10).configure(
                font='Segoe UI'
        ).configure_view(strokeWidth=0).configure_axis(grid=False, labelAngle=45).configure_text(size=11)

    else:
        final_chart = alt.hconcat(
            alt.hconcat(t1_tossups + player_grid, t1_score + total_grid, spacing=10),
            alt.hconcat(t2_tossups + player_grid, t2_score + total_grid, spacing=10),
            spacing=-10).configure(
                font='Segoe UI'
        ).configure_view(strokeWidth=0).configure_axis(grid=False, labelAngle=45).configure_text(size=11)

    return final_chart

def make_bpa_ppg_chart(df):
    char = alt.Chart(df).mark_point().encode(
        y=alt.Y('ACC', axis=alt.Axis(title='Avg. Correct Celerity')),
        x=alt.X('PPG', scale=alt.Scale(domain=[-10, 100])),
        tooltip=['player:O', 'team:O', 'PPG', 'ACC', 'BPA']
    )
    return char
