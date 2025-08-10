
import streamlit as st
import json
import pandas as pd

st.set_page_config(page_title="Gerador de Templates - 1Doc", page_icon="💬", layout="centered")

# ============ Carregar biblioteca ============
def load_library():
    try:
        with open("1doc_flow_templates_v3.json", "r", encoding="utf-8") as f:
            data = json.load(f)["templates_by_segment"]
            return data
    except Exception:
        with open("1doc_flow_templates.json", "r", encoding="utf-8") as f:
            # compatibilidade com versão antiga
            old = json.load(f).get("templates", {})
        # converter old para o novo formato mínimo (sem setores -> usar 'Geral')
        new = {}
        for seg, bloco in old.items():
            new.setdefault(seg, {"setores": {}})
            new[seg]["setores"]["Geral"] = {"rotinas": bloco.get("rotinas", [])}
        return new

LIB = load_library()
SEGMENTOS = sorted(list(LIB.keys()))

# lista de setores mestres para mostrar como opções (universal)
SETORES_MESTRES = [
    "Recursos Humanos", "Compras e Suprimentos", "Financeiro/Controladoria", "Fiscal/Tributário",
    "Jurídico", "Comercial e Vendas", "Marketing e Comunicação", "Tecnologia da Informação (TI)",
    "Operações/Facilities/Manutenção", "Qualidade/Compliance", "Logística/Transportes",
    "Segurança do Trabalho/SSMA", "Atendimento/CS"
]

# Helper de rerun
def _rerun():
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            pass

def add_message(role, content):
    st.session_state.messages.append({"role": role, "content": content})

def reset_session():
    st.session_state.stage = "ask_name"
    st.session_state.answers = {}
    st.session_state.selection = []
    st.session_state.messages = []
    add_message("assistant", "Oi! Sou o assistente de **gerador de templates** da 1Doc. Qual é o seu **nome**?")

def ensure_init():
    if "stage" not in st.session_state:
        st.session_state.stage = "ask_name"
    if "answers" not in st.session_state:
        st.session_state.answers = {}
    if "selection" not in st.session_state:
        st.session_state.selection = []
    if "messages" not in st.session_state:
        st.session_state.messages = []
        add_message("assistant", "Oi! Sou o assistente de **gerador de templates** da 1Doc. Qual é o seu **nome**?")

ensure_init()

st.title("💬 Gerador de Templates - 1Doc")
st.caption("Converse comigo para gerar **rotinas administrativas** por **segmento** e **setor** e baixar em CSV/JSON.")

with st.sidebar:
    if st.button("🔄 Recomeçar conversa"):
        reset_session()
        _rerun()

# Render histórico
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# input
user_input = st.chat_input("Digite aqui...")

# botões rápidos por etapa
def buttons(options, cols_count=3, key_prefix=""):
    if not options:
        return None
    cols_count = max(1, cols_count)
    clicked = None
    for i, opt in enumerate(options):
        if i % cols_count == 0:
            cols = st.columns(cols_count)
        if cols[i % cols_count].button(opt, key=f"{key_prefix}{opt}"):
            clicked = opt
    return clicked

def coletar_rotinas(seg, setores_escolhidos):
    # Retorna lista de dicts {setor, rotina, etapas}
    out = []
    blocos = LIB.get(seg, {}).get("setores", {})
    for setor in setores_escolhidos:
        rotinas = []
        if setor in blocos:
            rotinas = blocos[setor].get("rotinas", [])
        elif setor in SETORES_MESTRES and "Geral" in blocos:
            rotinas = blocos["Geral"].get("rotinas", [])
        # adicionar rotinas
        for r in rotinas:
            out.append({"setor": setor, "rotina": r.get("nome",""), "etapas": r.get("etapas", [])})
    return out

def mostrar_resultado(listagem, incluir_etapas):
    with st.chat_message("assistant"):
        if not listagem:
            st.markdown("Não encontrei rotinas para o que você selecionou.")
            return
        st.markdown("Perfeito! Aqui está **o que recomendo**:")
        for item in listagem:
            st.markdown(f"**Setor:** {item['setor']}")
            st.markdown(f"**Rotina:** {item['rotina']}")
            if incluir_etapas:
                for i, e in enumerate(item["etapas"], start=1):
                    st.write(f"{i}. {e}")
            st.write("---")
        # export
        rows = []
        for item in listagem:
            if incluir_etapas and item["etapas"]:
                for i, etapa in enumerate(item["etapas"], start=1):
                    rows.append({"Segmento": st.session_state.answers.get("segmento",""),
                                 "Setor": item["setor"], "Rotina": item["rotina"],
                                 "Etapa (ordem)": f"{i}. {etapa}"})
            else:
                rows.append({"Segmento": st.session_state.answers.get("segmento",""),
                             "Setor": item["setor"], "Rotina": item["rotina"], "Etapa (ordem)": ""})
        df = pd.DataFrame(rows)
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Baixar CSV", data=csv_bytes, file_name="fluxos_exportados.csv", mime="text/csv")
        json_bytes = json.dumps({"selecoes": listagem, "segmento": st.session_state.answers.get("segmento",""),
                                 "incluir_etapas": incluir_etapas}, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button("⬇️ Baixar JSON", data=json_bytes, file_name="fluxos_exportados.json", mime="application/json")

# Render stage-specific quick UIs
shortcut = None
stage = st.session_state.stage
if stage == "ask_business_type":
    with st.chat_message("assistant"):
        st.markdown("Agora me diga o **segmento** da instituição (ex.: Hospital, Tecnologia, Imobiliária).")
        filtro = st.text_input("Filtro rápido de segmento (opcional)", key="filtro_segmento_ui")
        opts = [s for s in SEGMENTOS if not filtro or filtro.lower() in s.lower()]
        shortcut = buttons(opts, cols_count=3, key_prefix="seg_")
elif stage == "ask_sector_scope":
    with st.chat_message("assistant"):
        st.markdown("Você quer **visualizar templates para todos setores da sua empresa** ou **apenas alguns**?")
        shortcut = buttons(["Todos os setores", "Escolher setores"], cols_count=2, key_prefix="scope_")
elif stage == "ask_sectors":
    with st.chat_message("assistant"):
        seg = st.session_state.answers.get("segmento")
        st.markdown(f"Selecione os **setores** para o segmento **{seg}**:")
        # setores disponíveis = união dos setores do segmento + mestres
        disponiveis = sorted(list(set(list(LIB.get(seg, {}).get("setores", {}).keys()) + SETORES_MESTRES)))
        escolhidos = st.multiselect("Setores", disponiveis, key="selec_setores")
        if st.button("Confirmar setores"):
            st.session_state.answers["setores"] = escolhidos if escolhidos else disponiveis
            st.session_state.stage = "ask_routine_scope"
            _rerun()
elif stage == "ask_routine_scope":
    with st.chat_message("assistant"):
        st.markdown("Quer ver **todas as sugestões de rotinas administrativas** para os setores escolhidos ou **selecionar rotinas específicas**?")
        shortcut = buttons(["Todas as rotinas", "Selecionar rotinas"], cols_count=2, key_prefix="rot_scope_")
elif stage == "ask_routines":
    with st.chat_message("assistant"):
        seg = st.session_state.answers.get("segmento")
        setores = st.session_state.answers.get("setores", [])
        st.markdown("Selecione as **rotinas** (por setor):")
        selecao = []
        for setor in setores:
            st.markdown(f"**{setor}**")
            blocos = LIB.get(seg, {}).get("setores", {})
            rotinas = []
            if setor in blocos:
                rotinas = [r.get("nome","") for r in blocos[setor].get("rotinas", [])]
            elif setor in SETORES_MESTRES and "Geral" in blocos:
                rotinas = [r.get("nome","") for r in blocos["Geral"].get("rotinas", [])]
            selecionadas = st.multiselect(f"Rotinas em {setor}", rotinas, key=f"rot_{setor}")
            for nome in selecionadas:
                # pegar etapas
                for r in (blocos.get(setor, {}).get("rotinas", []) + blocos.get("Geral", {}).get("rotinas", [])):
                    if r.get("nome") == nome:
                        selecao.append({"setor": setor, "rotina": nome, "etapas": r.get("etapas", [])})
                        break
        if st.button("Confirmar rotinas selecionadas"):
            st.session_state.selection = selecao
            st.session_state.stage = "ask_steps"
            _rerun()
elif stage == "ask_steps":
    with st.chat_message("assistant"):
        st.markdown("Deseja que eu **inclua as etapas** para essas rotinas?")
        shortcut = buttons(["Sim, incluir etapas", "Não, apenas a lista de rotinas"], cols_count=2, key_prefix="steps_")
elif stage == "show_result":
    incluir = st.session_state.answers.get("incluir_etapas", False)
    mostrar_resultado(st.session_state.selection, incluir)

# process user text or shortcut
if shortcut and not user_input:
    user_input = shortcut

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    stage = st.session_state.stage

    if stage == "ask_name":
        st.session_state.answers["nome"] = user_input.strip()
        add_message("assistant", f"Prazer, {st.session_state.answers['nome']}! Qual é o **nome da instituição**?")
        st.session_state.stage = "ask_institution"
        _rerun()

    elif stage == "ask_institution":
        st.session_state.answers["instituicao"] = user_input.strip()
        add_message("assistant", "Certo. Agora escolha o **segmento** da instituição.")
        st.session_state.stage = "ask_business_type"
        _rerun()

    elif stage == "ask_business_type":
        typed = user_input.strip()
        seg = None
        for s in SEGMENTOS:
            if typed.lower() == s.lower() or typed.lower() in s.lower():
                seg = s
                break
        if not seg:
            add_message("assistant", "Não reconheci esse segmento. Use um dos botões acima ou digite novamente.")
        else:
            st.session_state.answers["segmento"] = seg
            add_message("assistant", "Você quer **todos os setores** ou **apenas alguns**?")
            st.session_state.stage = "ask_sector_scope"
            _rerun()

    elif stage == "ask_sector_scope":
        choice = user_input.strip().lower()
        seg = st.session_state.answers.get("segmento")
        disponiveis = sorted(list(set(list(LIB.get(seg, {}).get("setores", {}).keys()) + SETORES_MESTRES)))
        if "todos" in choice:
            st.session_state.answers["setores"] = disponiveis
            add_message("assistant", "Perfeito. Quer ver **todas as sugestões de rotinas administrativas** para os setores ou **selecionar rotinas específicas**?")
            st.session_state.stage = "ask_routine_scope"
            _rerun()
        else:
            st.session_state.stage = "ask_sectors"
            _rerun()

    elif stage == "ask_routine_scope":
        choice = user_input.strip().lower()
        if "todas" in choice:
            seg = st.session_state.answers.get("segmento")
            setores = st.session_state.answers.get("setores", [])
            st.session_state.selection = coletar_rotinas(seg, setores)
            st.session_state.stage = "ask_steps"
            _rerun()
        else:
            st.session_state.stage = "ask_routines"
            _rerun()

    elif stage == "ask_steps":
        choice = user_input.strip().lower()
        st.session_state.answers["incluir_etapas"] = ("sim" in choice or "incluir" in choice or "etapa" in choice)
        st.session_state.stage = "show_result"
        _rerun()

    elif stage == "show_result":
        reset_session()
        _rerun()

st.caption("Dica: defina os **setores responsáveis** por etapa direto na 1Doc.")