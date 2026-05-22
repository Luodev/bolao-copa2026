import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, timedelta, timezone

# Timezone Brasil (UTC-3)
BR_TZ = timezone(timedelta(hours=-3))

# ─────────────────────────────────────────────
# BANDEIRAS DOS PAISES
# ─────────────────────────────────────────────
FLAGS = {
    "México": "🇲🇽",            "África do Sul": "🇿🇦",
    "Coreia do Sul": "🇰🇷",     "República Tcheca": "🇨🇿",
    "Canadá": "🇨🇦",            "Bósnia e Herzegovina": "🇧🇦",
    "Qatar": "🇶🇦",             "Suíça": "🇨🇭",
    "Brasil": "🇧🇷",            "Marrocos": "🇲🇦",
    "Haiti": "🇭🇹",             "Escócia": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "Estados Unidos": "🇺🇸",    "Paraguai": "🇵🇾",
    "Austrália": "🇦🇺",         "Turquia": "🇹🇷",
    "Alemanha": "🇩🇪",          "Curaçao": "🇨🇼",
    "Costa do Marfim": "🇨🇮",   "Equador": "🇪🇨",
    "Países Baixos": "🇳🇱",     "Japão": "🇯🇵",
    "Suécia": "🇸🇪",            "Tunísia": "🇹🇳",
    "Bélgica": "🇧🇪",           "Egito": "🇪🇬",
    "Irã": "🇮🇷",               "Nova Zelândia": "🇳🇿",
    "Espanha": "🇪🇸",           "Cabo Verde": "🇨🇻",
    "Arábia Saudita": "🇸🇦",    "Uruguai": "🇺🇾",
    "França": "🇫🇷",            "Senegal": "🇸🇳",
    "Iraque": "🇮🇶",            "Noruega": "🇳🇴",
    "Argentina": "🇦🇷",         "Argélia": "🇩🇿",
    "Áustria": "🇦🇹",           "Jordânia": "🇯🇴",
    "Portugal": "🇵🇹",          "Rep. Congo": "🇨🇩",
    "Uzbequistão": "🇺🇿",       "Colômbia": "🇨🇴",
    "Inglaterra": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",   "Croácia": "🇭🇷",
    "Gana": "🇬🇭",              "Panamá": "🇵🇦",
    "A definir": "⚽",
}

def flag(team: str) -> str:
    return FLAGS.get(team, "⚽")

def lbl(team: str) -> str:
    return f"{flag(team)} {team}"

# ─────────────────────────────────────────────
# UTILIDADES DE HORARIO
# ─────────────────────────────────────────────
def now_br():
    return datetime.now(BR_TZ)

def parse_dh(dh):
    """Aceita string ISO ou datetime — retorna datetime ciente de tz."""
    if not dh:
        return None
    if isinstance(dh, str):
        try:
            d = datetime.fromisoformat(dh.replace("Z", "+00:00"))
        except Exception:
            return None
    else:
        d = dh
    if d.tzinfo is None:
        d = d.replace(tzinfo=BR_TZ)
    return d.astimezone(BR_TZ)

def esta_travado(dh) -> bool:
    """Retorna True se o jogo ja comecou (apostas travadas)."""
    d = parse_dh(dh)
    if not d:
        return False
    return now_br() >= d

def contagem_regressiva(dh) -> str:
    """Formata a contagem ate o jogo ou 'apostas fechadas'."""
    d = parse_dh(dh)
    if not d:
        return "🕐 Horário a definir"
    delta = d - now_br()
    if delta.total_seconds() <= 0:
        return "🔒 Apostas fechadas"
    total = int(delta.total_seconds())
    dias = total // 86400
    horas = (total % 86400) // 3600
    mins = (total % 3600) // 60
    if dias > 0:
        return f"⏰ Falta {dias}d {horas}h"
    if horas > 0:
        return f"⏰ Falta {horas}h {mins}min"
    return f"⏰ Falta {mins}min"

def fmt_dh(dh) -> str:
    d = parse_dh(dh)
    if not d:
        return "—"
    return d.strftime("%d/%m %H:%M")

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Bolão Copa 2026",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# GAME DATA
# ─────────────────────────────────────────────
GROUPS = {
    "A": ["México", "África do Sul", "Coreia do Sul", "República Tcheca"],
    "B": ["Canadá", "Bósnia e Herzegovina", "Qatar", "Suíça"],
    "C": ["Brasil", "Marrocos", "Haiti", "Escócia"],
    "D": ["Estados Unidos", "Paraguai", "Austrália", "Turquia"],
    "E": ["Alemanha", "Curaçao", "Costa do Marfim", "Equador"],
    "F": ["Países Baixos", "Japão", "Suécia", "Tunísia"],
    "G": ["Bélgica", "Egito", "Irã", "Nova Zelândia"],
    "H": ["Espanha", "Cabo Verde", "Arábia Saudita", "Uruguai"],
    "I": ["França", "Senegal", "Iraque", "Noruega"],
    "J": ["Argentina", "Argélia", "Áustria", "Jordânia"],
    "K": ["Portugal", "Rep. Congo", "Uzbequistão", "Colômbia"],
    "L": ["Inglaterra", "Croácia", "Gana", "Panamá"],
}
MATCHUPS = [(0, 1), (2, 3), (0, 2), (1, 3), (0, 3), (1, 2)]
ROUNDS   = [1,      1,      2,      2,      3,      3     ]
KO_PHASES = [
    ("Oitavas de Final", 16),
    ("Quartas de Final", 8),
    ("Semifinal", 4),
    ("Disputa 3° Lugar", 1),
    ("Final", 1),
]


@st.cache_data
def build_games():
    games, num = [], 1
    for g, teams in GROUPS.items():
        for (i, j), rnd in zip(MATCHUPS, ROUNDS):
            games.append({
                "id": num, "fase": "Grupos", "grupo": g,
                "detalhe": f"Grupo {g} — Rodada {rnd}",
                "mandante": teams[i], "visitante": teams[j],
            })
            num += 1
    for phase, count in KO_PHASES:
        for k in range(count):
            label = f"{phase} — Jogo {k+1}" if count > 1 else phase
            games.append({
                "id": num, "fase": phase, "grupo": None,
                "detalhe": label,
                "mandante": "A definir", "visitante": "A definir",
            })
            num += 1
    return games  # 102 games total


ALL_GAMES = build_games()
GROUP_LETTERS = list(GROUPS.keys())
KO_FASE_NAMES = [p[0] for p in KO_PHASES]


# ─────────────────────────────────────────────
# SUPABASE
# ─────────────────────────────────────────────
@st.cache_resource
def get_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


db = get_db()


def clear_cache():
    get_participantes.clear()
    get_resultados.clear()
    get_palpites_part.clear()


@st.cache_data(ttl=20)
def get_participantes():
    return db.table("participantes").select("*").order("nome").execute().data


@st.cache_data(ttl=10)
def get_resultados():
    """Returns dict jogo_id -> {gols_mandante, gols_visitante, mandante, visitante}"""
    rows = db.table("resultados").select("*").execute().data
    return {r["jogo_id"]: r for r in rows}


@st.cache_data(ttl=10)
def get_palpites_part(participante_id: int):
    """Returns dict jogo_id -> {gols_mandante, gols_visitante}"""
    rows = db.table("palpites").select("*").eq("participante_id", participante_id).execute().data
    return {p["jogo_id"]: p for p in rows}


# ─────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────
def resultado_sinal(m, v):
    return 1 if m > v else (-1 if m < v else 0)


def calcular_pontos(pm, pv, rm, rv):
    if pm == rm and pv == rv:
        return 3
    if resultado_sinal(pm, pv) == resultado_sinal(rm, rv):
        return 1
    return 0


def calcular_ranking():
    resultados = get_resultados()
    partes = get_participantes()
    ranking = []
    for p in partes:
        palpites = get_palpites_part(p["id"])
        pts_g = pts_m = 0
        for jid, pal in palpites.items():
            res = resultados.get(jid)
            if res is None or res.get("gols_mandante") is None:
                continue
            pts = calcular_pontos(
                pal["gols_mandante"], pal["gols_visitante"],
                res["gols_mandante"], res["gols_visitante"],
            )
            # find game fase
            game = next((g for g in ALL_GAMES if g["id"] == jid), None)
            if game and game["fase"] == "Grupos":
                pts_g += pts
            else:
                pts_m += pts
        ranking.append({
            "nome": p["apelido"] or p["nome"],
            "nome_completo": p["nome"],
            "pts_grupos": pts_g,
            "pts_mata": pts_m,
            "total": pts_g + pts_m,
        })
    return sorted(ranking, key=lambda x: (-x["total"], x["nome"]))


# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stSidebar"] { background: #1a1a2e; }
[data-testid="stSidebar"] * { color: #eee !important; }

.page-title {
    font-size: 2rem; font-weight: 800; margin-bottom: 0.2rem;
    background: linear-gradient(90deg, #1E8449, #27AE60);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.subtitle { color: #888; font-size: 0.9rem; margin-bottom: 1.5rem; }

.rank-row {
    display: flex; align-items: center; gap: 12px;
    padding: 10px 16px; border-radius: 10px; margin: 3px 0;
    background: white; box-shadow: 0 1px 4px rgba(0,0,0,.07);
}
.rank-row.ouro  { border-left: 5px solid #F1C40F; }
.rank-row.prata { border-left: 5px solid #BDC3C7; }
.rank-row.bronze{ border-left: 5px solid #CD7F32; }
.rank-row.other { border-left: 5px solid #e0e0e0; }
.rk-pos  { font-size: 1.1rem; font-weight: 700; width: 36px; color: #555; }
.rk-nome { flex: 1; font-weight: 600; font-size: 1rem; }
.rk-det  { color: #888; font-size: 0.82rem; }
.rk-pts  { font-size: 1.4rem; font-weight: 800; color: #1E8449; min-width: 60px; text-align: right; }

.jogo-row {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 14px; border-radius: 8px; margin: 2px 0;
    background: white; box-shadow: 0 1px 3px rgba(0,0,0,.05);
    font-size: 0.9rem;
}
.jogo-num  { color: #aaa; width: 28px; text-align: right; flex-shrink: 0; }
.jogo-fase { color: #888; width: 130px; flex-shrink: 0; font-size: 0.78rem; }
.jogo-time { flex: 1; }
.jogo-res  { font-weight: 700; width: 60px; text-align: center; color: #1E8449; }
.jogo-pend { color: #ccc; width: 60px; text-align: center; }

.badge-fim   { background:#d5f5e3; color:#1e8449; border-radius:6px; padding:2px 8px; font-size:.75rem; }
.badge-pend  { background:#fef9e7; color:#b7950b; border-radius:6px; padding:2px 8px; font-size:.75rem; }

div[data-testid="stNumberInput"] input { text-align: center; font-weight: 600; }

.pts-card {
    border-radius: 14px; padding: 24px 28px; margin: 8px 0;
    display: flex; align-items: flex-start; gap: 20px;
}
.pts-card.exato  { background: linear-gradient(135deg, #d5f5e3, #a9dfbf); border-left: 6px solid #1E8449; }
.pts-card.result { background: linear-gradient(135deg, #fef9e7, #fdebd0); border-left: 6px solid #F39C12; }
.pts-card.errou  { background: linear-gradient(135deg, #f9ebea, #f5cac3); border-left: 6px solid #E74C3C; }
.pts-icon  { font-size: 2.2rem; line-height: 1; }
.pts-valor { font-size: 2.5rem; font-weight: 900; line-height: 1; }
.pts-exato { color: #1E8449; }
.pts-res   { color: #D35400; }
.pts-erro  { color: #C0392B; }
.pts-titulo{ font-size: 1.1rem; font-weight: 700; margin-bottom: 4px; }
.pts-desc  { font-size: 0.88rem; color: #555; line-height: 1.5; }
.pts-ex    { font-size: 0.82rem; color: #777; margin-top: 6px;
             background: rgba(255,255,255,0.6); border-radius: 6px; padding: 5px 10px; }

.group-card {
    background: white; border-radius: 10px; padding: 14px 18px;
    margin: 6px 0; box-shadow: 0 1px 4px rgba(0,0,0,.06);
}
.group-title { font-weight: 700; color: #1a1a2e; margin-bottom: 6px; font-size: 0.95rem; }
.group-team  { padding: 3px 0; font-size: 0.88rem; color: #444; border-bottom: 1px solid #f0f0f0; }
.group-team:last-child { border-bottom: none; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ Bolão Copa 2026")
    st.markdown("---")
    pagina = st.radio(
        "Menu",
        ["🏆 Ranking", "📝 Meus Palpites", "⚽ Jogos", "👥 Participantes", "📖 Como Pontua", "🔒 Admin"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown("""
    <div style='font-size:0.75rem; color:#aaa; line-height:1.6'>
    🥇 Placar exato → <b style='color:#F1C40F'>3 pts</b><br>
    🟡 Resultado certo → <b style='color:#aaa'>1 pt</b><br>
    ❌ Errou → <b style='color:#aaa'>0 pts</b>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    st.caption("Copa do Mundo 2026\nEUA · Canadá · México")


# ═══════════════════════════════════════════════════════════
#  🏆 RANKING
# ═══════════════════════════════════════════════════════════
if pagina == "🏆 Ranking":
    st.markdown('<p class="page-title">🏆 Ranking</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Pontuação atualizada automaticamente</p>', unsafe_allow_html=True)

    if st.button("🔄 Atualizar", key="refresh_rank"):
        clear_cache()
        st.rerun()

    ranking = calcular_ranking()

    if not ranking:
        st.info("Nenhum participante cadastrado ainda.")
    else:
        medals = {1: ("🥇", "ouro"), 2: ("🥈", "prata"), 3: ("🥉", "bronze")}
        for i, p in enumerate(ranking, 1):
            emoji, cls = medals.get(i, (f"{i}°", "other"))
            st.markdown(f"""
            <div class="rank-row {cls}">
                <div class="rk-pos">{emoji}</div>
                <div class="rk-nome">{p['nome']}
                    <div class="rk-det">Grupos: {p['pts_grupos']} pts &nbsp;|&nbsp; Mata: {p['pts_mata']} pts</div>
                </div>
                <div class="rk-pts">{p['total']} pts</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Pontuação tabela
        with st.expander("Ver tabela completa"):
            df = pd.DataFrame(ranking)[["nome", "pts_grupos", "pts_mata", "total"]].copy()
            df.index = range(1, len(df) + 1)
            df.columns = ["Nome", "Pts Grupos", "Pts Mata-Mata", "Total"]
            st.dataframe(df, use_container_width=True)


# ═══════════════════════════════════════════════════════════
#  📝 MEUS PALPITES
# ═══════════════════════════════════════════════════════════
elif pagina == "📝 Meus Palpites":
    st.markdown('<p class="page-title">📝 Meus Palpites</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Selecione seu nome e preencha seus palpites</p>', unsafe_allow_html=True)

    partes = get_participantes()
    if not partes:
        st.warning("Nenhum participante cadastrado. Acesse 👥 Participantes primeiro.")
        st.stop()

    nome_sel = st.selectbox("Seu nome:", [p["nome"] for p in partes])
    part = next(p for p in partes if p["nome"] == nome_sel)
    part_id = part["id"]

    resultados = get_resultados()
    palpites   = get_palpites_part(part_id)

    tab_g, tab_m = st.tabs(["⚽ Fase de Grupos (72 jogos)", "🏆 Mata-Mata (30 jogos)"])

    # ── GRUPOS ──────────────────────────────────────
    with tab_g:
        grupo_sel = st.selectbox(
            "Selecionar grupo:",
            [f"Grupo {g}" for g in GROUP_LETTERS],
            key="grp_sel",
        )
        letra = grupo_sel.split(" ")[1]
        games_grp = [g for g in ALL_GAMES if g.get("grupo") == letra]

        st.info(
            "💡 Preencha os gols previstos. Apostas travam automaticamente quando o jogo começa."
        )

        with st.form(f"form_grupo_{letra}"):
            palpites_form: dict[int, tuple] = {}

            for game in games_grp:
                res = resultados.get(game["id"])
                pal = palpites.get(game["id"], {})
                dh = (res or {}).get("data_hora")
                tem_resultado = res is not None and res.get("gols_mandante") is not None
                travado_hora = esta_travado(dh)
                bloqueado = tem_resultado or travado_hora

                st.markdown(f"**{game['detalhe']}** &nbsp;·&nbsp; <span style='color:#888;font-size:0.85rem'>{fmt_dh(dh) if dh else 'Horário a definir'}</span>", unsafe_allow_html=True)
                col_m, col_x, col_v = st.columns([5, 1, 5])
                col_m.markdown(f"🏠 {lbl(game['mandante'])}")
                col_x.markdown("**×**")
                col_v.markdown(f"{lbl(game['visitante'])} ✈️")

                col_pm, col_pv, col_status = st.columns([1, 1, 4])
                if tem_resultado:
                    col_pm.markdown(f"### {res['gols_mandante']}")
                    col_pv.markdown(f"### {res['gols_visitante']}")
                    col_status.markdown(
                        f"<span class='badge-fim'>✅ Resultado lançado</span> "
                        f"— Seu palpite: {pal.get('gols_mandante', '—')} × {pal.get('gols_visitante', '—')}",
                        unsafe_allow_html=True,
                    )
                elif travado_hora:
                    col_pm.markdown(f"### {pal.get('gols_mandante','—')}")
                    col_pv.markdown(f"### {pal.get('gols_visitante','—')}")
                    col_status.markdown(
                        "<span class='badge-fim' style='background:#fadbd8;color:#943126'>🔒 Apostas fechadas (jogo iniciado)</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    pm = col_pm.number_input(
                        "M", min_value=0, max_value=20,
                        value=int(pal.get("gols_mandante", 0)),
                        key=f"gm_{game['id']}", label_visibility="collapsed",
                    )
                    pv = col_pv.number_input(
                        "V", min_value=0, max_value=20,
                        value=int(pal.get("gols_visitante", 0)),
                        key=f"gv_{game['id']}", label_visibility="collapsed",
                    )
                    col_status.markdown(
                        f"<span class='badge-pend'>{contagem_regressiva(dh)}</span>",
                        unsafe_allow_html=True,
                    )
                    palpites_form[game["id"]] = (pm, pv)
                st.divider()

            submitted = st.form_submit_button(
                f"💾 Salvar Palpites — {grupo_sel}", use_container_width=True, type="primary"
            )

        if submitted:
            salvos, bloqueados = 0, 0
            for jid, (pm, pv) in palpites_form.items():
                res = resultados.get(jid)
                if esta_travado((res or {}).get("data_hora")):
                    bloqueados += 1
                    continue
                if jid in palpites:
                    db.table("palpites").update(
                        {"gols_mandante": pm, "gols_visitante": pv}
                    ).eq("id", palpites[jid]["id"]).execute()
                else:
                    db.table("palpites").insert(
                        {"participante_id": part_id, "jogo_id": jid,
                         "gols_mandante": pm, "gols_visitante": pv}
                    ).execute()
                salvos += 1
            clear_cache()
            msg = f"✅ {salvos} palpite(s) salvo(s)."
            if bloqueados:
                msg += f" ⚠️ {bloqueados} jogo(s) já iniciado(s) e foram ignorados."
            st.success(msg)
            st.rerun()

    # ── MATA-MATA ────────────────────────────────────
    with tab_m:
        fase_sel = st.selectbox("Selecionar fase:", KO_FASE_NAMES, key="ko_sel")
        games_ko = [g for g in ALL_GAMES if g["fase"] == fase_sel]

        st.info(
            "💡 Os nomes dos times são atualizados pelo admin conforme avançam. "
            "Preencha seus palpites mesmo com 'A definir'."
        )

        with st.form(f"form_ko_{fase_sel}"):
            palpites_ko: dict[int, tuple] = {}

            for game in games_ko:
                res = resultados.get(game["id"])
                pal = palpites.get(game["id"], {})
                dh = (res or {}).get("data_hora")
                tem_resultado = res is not None and res.get("gols_mandante") is not None
                travado_hora = esta_travado(dh)

                mandante  = (res or {}).get("mandante") or game["mandante"]
                visitante = (res or {}).get("visitante") or game["visitante"]

                st.markdown(f"**{game['detalhe']}** &nbsp;·&nbsp; <span style='color:#888;font-size:0.85rem'>{fmt_dh(dh) if dh else 'Horário a definir'}</span>", unsafe_allow_html=True)
                col_m, col_x, col_v = st.columns([5, 1, 5])
                col_m.markdown(f"🏠 {lbl(mandante)}")
                col_x.markdown("**×**")
                col_v.markdown(f"{lbl(visitante)} ✈️")

                col_pm, col_pv, col_status = st.columns([1, 1, 4])
                if tem_resultado:
                    col_pm.markdown(f"### {res['gols_mandante']}")
                    col_pv.markdown(f"### {res['gols_visitante']}")
                    col_status.markdown(
                        f"<span class='badge-fim'>✅ Resultado lançado</span> "
                        f"— Seu palpite: {pal.get('gols_mandante','—')} × {pal.get('gols_visitante','—')}",
                        unsafe_allow_html=True,
                    )
                elif travado_hora:
                    col_pm.markdown(f"### {pal.get('gols_mandante','—')}")
                    col_pv.markdown(f"### {pal.get('gols_visitante','—')}")
                    col_status.markdown(
                        "<span class='badge-fim' style='background:#fadbd8;color:#943126'>🔒 Apostas fechadas (jogo iniciado)</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    pm = col_pm.number_input(
                        "M", min_value=0, max_value=20,
                        value=int(pal.get("gols_mandante", 0)),
                        key=f"km_{game['id']}", label_visibility="collapsed",
                    )
                    pv = col_pv.number_input(
                        "V", min_value=0, max_value=20,
                        value=int(pal.get("gols_visitante", 0)),
                        key=f"kv_{game['id']}", label_visibility="collapsed",
                    )
                    col_status.markdown(
                        f"<span class='badge-pend'>{contagem_regressiva(dh)}</span>",
                        unsafe_allow_html=True,
                    )
                    palpites_ko[game["id"]] = (pm, pv)
                st.divider()

            submitted_ko = st.form_submit_button(
                f"💾 Salvar Palpites — {fase_sel}", use_container_width=True, type="primary"
            )

        if submitted_ko:
            salvos, bloqueados = 0, 0
            for jid, (pm, pv) in palpites_ko.items():
                res = resultados.get(jid)
                if esta_travado((res or {}).get("data_hora")):
                    bloqueados += 1
                    continue
                if jid in palpites:
                    db.table("palpites").update(
                        {"gols_mandante": pm, "gols_visitante": pv}
                    ).eq("id", palpites[jid]["id"]).execute()
                else:
                    db.table("palpites").insert(
                        {"participante_id": part_id, "jogo_id": jid,
                         "gols_mandante": pm, "gols_visitante": pv}
                    ).execute()
                salvos += 1
            clear_cache()
            msg = f"✅ {salvos} palpite(s) salvo(s)."
            if bloqueados:
                msg += f" ⚠️ {bloqueados} jogo(s) já iniciado(s) foram ignorados."
            st.success(msg)
            st.rerun()


# ═══════════════════════════════════════════════════════════
#  ⚽ JOGOS
# ═══════════════════════════════════════════════════════════
elif pagina == "⚽ Jogos":
    st.markdown('<p class="page-title">⚽ Jogos e Resultados</p>', unsafe_allow_html=True)

    resultados = get_resultados()

    fase_opts = ["Todos", "Grupos"] + KO_FASE_NAMES
    filtro = st.selectbox("Filtrar por fase:", fase_opts)

    games_view = ALL_GAMES if filtro == "Todos" else [g for g in ALL_GAMES if g["fase"] == filtro]

    total = len(games_view)
    finalizados = sum(1 for g in games_view if resultados.get(g["id"], {}).get("gols_mandante") is not None)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de jogos", total)
    col2.metric("Finalizados", finalizados)
    col3.metric("Pendentes", total - finalizados)

    st.markdown("<br>", unsafe_allow_html=True)

    for game in games_view:
        res = resultados.get(game["id"])
        mandante  = (res or {}).get("mandante") or game["mandante"]
        visitante = (res or {}).get("visitante") or game["visitante"]
        dh = (res or {}).get("data_hora")

        if res and res.get("gols_mandante") is not None:
            gm, gv = res["gols_mandante"], res["gols_visitante"]
            resultado_html = f'<div class="jogo-res">{gm} × {gv}</div>'
            badge = '<span class="badge-fim">✅</span>'
            status_txt = fmt_dh(dh) if dh else ""
        elif esta_travado(dh):
            resultado_html = '<div class="jogo-pend">🔴 AO VIVO</div>'
            badge = '<span class="badge-pend" style="background:#fadbd8;color:#943126">⚽</span>'
            status_txt = fmt_dh(dh)
        else:
            resultado_html = '<div class="jogo-pend">— × —</div>'
            badge = '<span class="badge-pend">⏳</span>'
            status_txt = contagem_regressiva(dh)

        st.markdown(f"""
        <div class="jogo-row">
            <div class="jogo-num">#{game['id']}</div>
            <div class="jogo-fase">{game['detalhe']}<br><span style="color:#aaa;font-size:0.7rem">{status_txt}</span></div>
            <div class="jogo-time">{lbl(mandante)}</div>
            {resultado_html}
            <div class="jogo-time" style="text-align:right">{lbl(visitante)}</div>
            {badge}
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  👥 PARTICIPANTES
# ═══════════════════════════════════════════════════════════
elif pagina == "👥 Participantes":
    st.markdown('<p class="page-title">👥 Participantes</p>', unsafe_allow_html=True)

    partes = get_participantes()

    if partes:
        df = pd.DataFrame(partes)[["nome", "apelido"]].rename(
            columns={"nome": "Nome", "apelido": "Apelido"}
        )
        df.index = range(1, len(df) + 1)
        st.dataframe(df, use_container_width=True)
        st.caption(f"{len(partes)} participante(s) cadastrado(s)")
    else:
        st.info("Nenhum participante cadastrado ainda.")

    st.markdown("---")
    st.subheader("Cadastrar novo participante")

    with st.form("form_part"):
        col1, col2 = st.columns(2)
        nome    = col1.text_input("Nome *")
        apelido = col2.text_input("Apelido (opcional)")

        if st.form_submit_button("✅ Cadastrar", type="primary"):
            if not nome.strip():
                st.error("Nome é obrigatório.")
            elif any(p["nome"].lower() == nome.strip().lower() for p in partes):
                st.error("Já existe um participante com esse nome.")
            else:
                db.table("participantes").insert({
                    "nome": nome.strip(),
                    "apelido": apelido.strip() or None,
                }).execute()
                clear_cache()
                st.success(f"✅ {nome.strip()} cadastrado!")
                st.rerun()


# ═══════════════════════════════════════════════════════════
#  📖 COMO PONTUA
# ═══════════════════════════════════════════════════════════
elif pagina == "📖 Como Pontua":
    st.markdown('<p class="page-title">📖 Como Funciona a Pontuação</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Entenda como os pontos são calculados</p>', unsafe_allow_html=True)

    # Cards de pontuação
    st.markdown("""
    <div class="pts-card exato">
        <div class="pts-icon">🎯</div>
        <div>
            <div style="display:flex;align-items:baseline;gap:10px">
                <div class="pts-valor pts-exato">3 pts</div>
                <div class="pts-titulo">Placar Exato</div>
            </div>
            <div class="pts-desc">Você acertou o número exato de gols dos dois times.</div>
            <div class="pts-ex">✅ Exemplo: você palpitou <b>Brasil 2 × 1 França</b> e o resultado foi <b>Brasil 2 × 1 França</b></div>
        </div>
    </div>

    <div class="pts-card result">
        <div class="pts-icon">🟡</div>
        <div>
            <div style="display:flex;align-items:baseline;gap:10px">
                <div class="pts-valor pts-res">1 pt</div>
                <div class="pts-titulo">Resultado Certo (sem placar exato)</div>
            </div>
            <div class="pts-desc">Você acertou quem ganhou ou que seria empate, mas errou o placar.</div>
            <div class="pts-ex">🟡 Exemplo: você palpitou <b>Brasil 3 × 0 França</b> e o resultado foi <b>Brasil 1 × 0 França</b> — ambos vitória do Brasil</div>
        </div>
    </div>

    <div class="pts-card errou">
        <div class="pts-icon">❌</div>
        <div>
            <div style="display:flex;align-items:baseline;gap:10px">
                <div class="pts-valor pts-erro">0 pts</div>
                <div class="pts-titulo">Resultado Errado</div>
            </div>
            <div class="pts-desc">Você errou quem ganhou (ou empate).</div>
            <div class="pts-ex">❌ Exemplo: você palpitou <b>Brasil 2 × 0 França</b> e o resultado foi <b>França 1 × 0 Brasil</b></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabela resumo
    st.subheader("📊 Tabela de Pontos")
    col1, col2, col3 = st.columns(3)
    col1.metric("Placar exato", "3 pontos", "máximo por jogo")
    col2.metric("Resultado certo", "1 ponto", "vitória/empate/derrota")
    col3.metric("Resultado errado", "0 pontos", "")

    st.markdown("<br>", unsafe_allow_html=True)

    # Exemplos práticos
    st.subheader("📝 Exemplos Práticos")
    exemplos = [
        ("Brasil 2 × 1 Argentina", "Brasil 2 × 1 Argentina", "🎯 Placar exato", 3, "#d5f5e3"),
        ("Brasil 3 × 0 Argentina", "Brasil 2 × 1 Argentina", "🟡 Vitória Brasil (certo)", 1, "#fef9e7"),
        ("Empate 1 × 1",           "Empate 0 × 0",           "🟡 Empate (certo)",         1, "#fef9e7"),
        ("Argentina 1 × 0 Brasil", "Brasil 2 × 0 Argentina", "❌ Resultado errado",       0, "#f9ebea"),
    ]
    for palpite, resultado, descricao, pts, cor in exemplos:
        st.markdown(f"""
        <div style="background:{cor};border-radius:8px;padding:10px 16px;margin:4px 0;
                    display:flex;align-items:center;gap:16px;font-size:0.9rem">
            <div style="flex:1"><b>Palpite:</b> {palpite}</div>
            <div style="flex:1"><b>Resultado:</b> {resultado}</div>
            <div style="flex:1">{descricao}</div>
            <div style="font-size:1.3rem;font-weight:800;min-width:50px;text-align:right">
                {'+' if pts > 0 else ''}{pts} pts
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Grupos da copa
    st.subheader("🌍 Grupos da Copa 2026")
    cols = st.columns(4)
    for idx, (letra, times) in enumerate(GROUPS.items()):
        with cols[idx % 4]:
            times_html = "".join(f'<div class="group-team">{"🏠 " if i==0 else "  "}{t}</div>' for i, t in enumerate(times))
            st.markdown(f"""
            <div class="group-card">
                <div class="group-title">Grupo {letra}</div>
                {times_html}
            </div>
            """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  🔒 ADMIN
# ═══════════════════════════════════════════════════════════
elif pagina == "🔒 Admin":
    st.markdown('<p class="page-title">🔒 Painel Admin</p>', unsafe_allow_html=True)

    if not st.session_state.get("admin_ok"):
        with st.form("login_admin"):
            senha = st.text_input("Senha:", type="password")
            if st.form_submit_button("Entrar", type="primary"):
                if senha == st.secrets.get("ADMIN_PASSWORD", "copa2026admin"):
                    st.session_state["admin_ok"] = True
                    st.rerun()
                else:
                    st.error("Senha incorreta.")
        st.stop()

    st.success("✅ Modo administrador ativo")
    if st.button("🚪 Sair do admin"):
        st.session_state["admin_ok"] = False
        st.rerun()

    tab_res, tab_horarios, tab_times, tab_init = st.tabs(
        ["⚽ Lançar Resultados", "🕐 Horários dos Jogos", "🔄 Atualizar Times (Mata-Mata)", "🗄️ Inicializar BD"]
    )

    # ── RESULTADOS ───────────────────────────────────────
    with tab_res:
        st.subheader("Lançar Resultados Reais")

        resultados = get_resultados()

        fase_admin = st.selectbox(
            "Fase:", ["Grupos"] + KO_FASE_NAMES, key="admin_fase"
        )
        if fase_admin == "Grupos":
            grupo_admin = st.selectbox(
                "Grupo:", [f"Grupo {g}" for g in GROUP_LETTERS], key="admin_grupo"
            )
            letra_a = grupo_admin.split(" ")[1]
            games_admin = [g for g in ALL_GAMES if g.get("grupo") == letra_a]
        else:
            games_admin = [g for g in ALL_GAMES if g["fase"] == fase_admin]

        for game in games_admin:
            res = resultados.get(game["id"], {})
            mandante  = res.get("mandante") or game["mandante"]
            visitante = res.get("visitante") or game["visitante"]

            with st.expander(
                f"**Jogo {game['id']}** — {mandante} × {visitante}  "
                f"{'✅' if res.get('gols_mandante') is not None else '⏳'}"
            ):
                col1, col2, col3 = st.columns([3, 1, 3])
                gm = col1.number_input(
                    f"Gols {mandante}", min_value=0, max_value=30,
                    value=int(res.get("gols_mandante") or 0),
                    key=f"adm_gm_{game['id']}",
                )
                col2.markdown("### ×")
                gv = col3.number_input(
                    f"Gols {visitante}", min_value=0, max_value=30,
                    value=int(res.get("gols_visitante") or 0),
                    key=f"adm_gv_{game['id']}",
                )
                if st.button("💾 Salvar", key=f"save_{game['id']}", type="primary"):
                    payload = {
                        "jogo_id": game["id"],
                        "gols_mandante": gm,
                        "gols_visitante": gv,
                        "mandante": mandante,
                        "visitante": visitante,
                    }
                    if res:
                        db.table("resultados").update(payload).eq("jogo_id", game["id"]).execute()
                    else:
                        db.table("resultados").insert(payload).execute()
                    clear_cache()
                    st.success(f"✅ {gm} × {gv} salvo!")
                    st.rerun()

    # ── HORARIOS DOS JOGOS ───────────────────────────────
    with tab_horarios:
        st.subheader("🕐 Definir Data e Hora dos Jogos")
        st.info(
            "Defina o horário de cada jogo. As apostas dos participantes "
            "**travam automaticamente** quando o horário do jogo chega. "
            "Horário em **Brasília (UTC-3)**."
        )

        resultados = get_resultados()

        fase_h = st.selectbox(
            "Fase:", ["Grupos"] + KO_FASE_NAMES, key="hor_fase"
        )
        if fase_h == "Grupos":
            grupo_h = st.selectbox(
                "Grupo:", [f"Grupo {g}" for g in GROUP_LETTERS], key="hor_grupo"
            )
            letra_h = grupo_h.split(" ")[1]
            games_h = [g for g in ALL_GAMES if g.get("grupo") == letra_h]
        else:
            games_h = [g for g in ALL_GAMES if g["fase"] == fase_h]

        # Set all at once option
        with st.expander("⚡ Definir TODOS os horários desta fase de uma vez"):
            colA, colB, colC = st.columns(3)
            data_base = colA.date_input("Data inicial:", key="bulk_data")
            hora_base = colB.time_input("Hora do 1º jogo:", key="bulk_hora")
            intervalo_h = colC.number_input("Horas entre jogos:", 1, 24, 3, key="bulk_int")
            if st.button("✨ Aplicar para todos abaixo", key="bulk_btn"):
                from datetime import datetime as _dt, timedelta as _td
                cur = _dt.combine(data_base, hora_base).replace(tzinfo=BR_TZ)
                for game in games_h:
                    iso = cur.isoformat()
                    res = resultados.get(game["id"])
                    mandante  = (res or {}).get("mandante") or game["mandante"]
                    visitante = (res or {}).get("visitante") or game["visitante"]
                    payload = {
                        "jogo_id": game["id"], "data_hora": iso,
                        "mandante": mandante, "visitante": visitante,
                    }
                    if res:
                        db.table("resultados").update({"data_hora": iso}).eq("jogo_id", game["id"]).execute()
                    else:
                        db.table("resultados").insert(payload).execute()
                    cur += _td(hours=intervalo_h)
                clear_cache()
                st.success(f"✅ Horários definidos para {len(games_h)} jogos!")
                st.rerun()

        st.markdown("---")
        st.subheader("Ou definir um por um:")

        for game in games_h:
            res = resultados.get(game["id"], {})
            mandante  = res.get("mandante") or game["mandante"]
            visitante = res.get("visitante") or game["visitante"]
            dh_atual = parse_dh(res.get("data_hora"))

            with st.expander(
                f"#{game['id']}  {lbl(mandante)} × {lbl(visitante)}  ·  "
                f"{fmt_dh(res.get('data_hora')) if res.get('data_hora') else '— sem horário —'}"
            ):
                col1, col2, col3 = st.columns([2, 2, 1])
                d_val = dh_atual.date() if dh_atual else None
                t_val = dh_atual.time().replace(second=0, microsecond=0) if dh_atual else None
                data_in = col1.date_input("Data", value=d_val, key=f"dt_{game['id']}")
                hora_in = col2.time_input("Hora", value=t_val, key=f"hr_{game['id']}")
                if col3.button("💾 Salvar", key=f"sh_{game['id']}", type="primary"):
                    if data_in and hora_in:
                        from datetime import datetime as _dt
                        iso = _dt.combine(data_in, hora_in).replace(tzinfo=BR_TZ).isoformat()
                        if res:
                            db.table("resultados").update({"data_hora": iso}).eq("jogo_id", game["id"]).execute()
                        else:
                            db.table("resultados").insert({
                                "jogo_id": game["id"], "data_hora": iso,
                                "mandante": mandante, "visitante": visitante,
                            }).execute()
                        clear_cache()
                        st.success(f"✅ Horário {fmt_dh(iso)} salvo!")
                        st.rerun()
                    else:
                        st.error("Defina data e hora.")

    # ── TIMES MATA-MATA ──────────────────────────────────
    with tab_times:
        st.subheader("Atualizar Nomes dos Times (Mata-Mata)")
        st.info("Atualize os times conforme avançam para o mata-mata.")

        resultados = get_resultados()
        fase_times = st.selectbox("Fase:", KO_FASE_NAMES, key="ko_times_fase")
        games_ko_t = [g for g in ALL_GAMES if g["fase"] == fase_times]

        for game in games_ko_t:
            res = resultados.get(game["id"], {})
            with st.expander(f"Jogo {game['id']} — {game['detalhe']}"):
                col1, col2 = st.columns(2)
                m = col1.text_input("Mandante", value=res.get("mandante", game["mandante"]), key=f"tm_{game['id']}")
                v = col2.text_input("Visitante", value=res.get("visitante", game["visitante"]), key=f"tv_{game['id']}")
                if st.button("Atualizar", key=f"upd_{game['id']}"):
                    payload = {"jogo_id": game["id"], "mandante": m, "visitante": v}
                    if res:
                        db.table("resultados").update({"mandante": m, "visitante": v}).eq("jogo_id", game["id"]).execute()
                    else:
                        db.table("resultados").insert(payload).execute()
                    clear_cache()
                    st.success("✅ Times atualizados!")
                    st.rerun()

    # ── INICIALIZAR BD ───────────────────────────────────
    with tab_init:
        st.subheader("Inicializar Banco de Dados")
        st.warning(
            "⚠️ Execute este passo **apenas uma vez** após criar as tabelas no Supabase. "
            "Não apaga dados existentes."
        )
        st.markdown("""
        **Antes de clicar, execute este SQL no Supabase (SQL Editor):**
        ```sql
        -- Colar o conteúdo do arquivo setup_db.sql
        ```
        """)
        if st.button("🗄️ Verificar conexão com BD", type="primary"):
            try:
                db.table("participantes").select("id").limit(1).execute()
                db.table("resultados").select("id").limit(1).execute()
                db.table("palpites").select("id").limit(1).execute()
                st.success("✅ Conexão OK! Todas as tabelas encontradas.")
            except Exception as e:
                st.error(f"Erro: {e}\n\nVerifique se o SQL foi executado e as credenciais estão corretas.")
