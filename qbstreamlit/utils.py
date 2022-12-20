import re
import streamlit as st
import qbstreamlit.parser

def local_css(file_name):
    st.markdown('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Inconsolata&display=swap" rel="stylesheet">', unsafe_allow_html=True)
    st.markdown('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@48,400,0,0" />', unsafe_allow_html=True)
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def sanitize_answer(answer, remove_formatting = True, remove_alternate_answers = True):
    if remove_formatting:
        answer = re.sub(r'\<b\>', '', answer)
        answer = re.sub(r'\<i\>', '', answer)
        answer = re.sub(r'\</b\>', '', answer)
        answer = re.sub(r'\</i\>', '', answer)
        answer = re.sub(r'\</u\>', '', answer)
        answer = re.sub(r'\<u\>', '', answer)
        answer = re.sub(r'\<em\>', '', answer)
        answer = re.sub(r'\</em\>', '', answer)
    if remove_alternate_answers:
        answer = re.sub(r'\s\[.*', '', answer)
        answer = re.sub(r'\s\(.*', '', answer)

    return answer

def hr():
    return st.markdown('<hr>', unsafe_allow_html=True)


def fill_out_tossup_values(df, powers = True):
    if powers:
        tossup_values = ['P', 'G', 'N']
    else:
        tossup_values = ['G', 'N']
    for entry in tossup_values:
        if entry not in list(df):
            df[entry] = 0
    return df

def calc_pts(df):
    if st.session_state.powers:
        return df.P*15 + df.G*10 - df.N*5
    else:
        return df.G*10 - df.N*5

def populate_db():
    qbstreamlit.parser.populate_db_qbjs_nasat(st.session_state.tournament)
    qbstreamlit.parser.populate_db_packets_nasat(st.session_state.tournament)

