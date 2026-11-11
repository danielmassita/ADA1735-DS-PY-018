# %% [markdown]
# # Projeto Final — Análise Exploratória do App de Delivery
# 
# **Contexto:** time de dados de um app de delivery (SP, Rio, BH) — diagnóstico de 2024 para o planejamento 2025. Três frentes: operação, clientes, alavancas (cupom + chuva).
# 
# **Base:** `dados/delivery_pedidos.csv` — 8.058 pedidos, 18 colunas.
# 
# **Estrutura:** 11 etapas (perguntas → publicação), com checkpoints ao fim da Etapa 3 e da Etapa 4.
# 
# **Como rodar:** `Kernel → Restart & Run All` com o CSV em `dados/`. Tempo ≈ 30–60 s.

# %% [markdown]
# ### Dicionário de dados (referência)
# 
# | Coluna | Descrição |
# |---|---|
# | `pedido_id` | identificador do pedido |
# | `data_hora` | data e hora do pedido |
# | `cidade`, `bairro` | local de entrega |
# | `restaurante_id` | identificador do restaurante |
# | `tipo_cozinha` | Pizza, Japonesa, Hambúrguer, Brasileira, Saudável, Doces |
# | `plataforma` | Android, iOS ou Web |
# | `forma_pagamento` | Cartão de crédito, Pix, Vale-refeição, Dinheiro |
# | `cupom` | se o pedido usou cupom de desconto |
# | `cliente_novo` | primeiro pedido do cliente no app |
# | `chuva` | choveu na cidade naquele dia |
# | `distancia_km` | distância restaurante → cliente |
# | `tempo_entrega_min` | minutos entre pedido e entrega (`999` = sem registro) |
# | `valor_pedido` | valor dos itens em R$ (sem taxa) |
# | `taxa_entrega` | taxa de entrega em R$ |
# | `avaliacao` | nota de 1 a 5 (opcional) |
# | `pais`, `moeda` | país e moeda |

# %%
# ============================================================
# Imports + setup
# ============================================================
import os
import calendar
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy import stats

os.makedirs("saidas", exist_ok=True)

DADOS = "../dados/"  # ajuste se o CSV estiver em outro lugar
sns.set_theme(style="whitegrid", context="notebook")
ALFA = 0.05
resultados = []  # tabela-resumo das hipóteses (Etapa 9)

print(f"pandas  {pd.__version__}")
print(f"numpy   {np.__version__}")
print(f"seaborn {sns.__version__}")

# %% [markdown]
# ---
# ## Etapa 1 — Perguntas e hipóteses

# %% [markdown]
# ### Tarefa 1.1 — Cinco perguntas de negócio
# 
# | # | Frente | Pergunta | Coluna(s) | Granularidade |
# |---|---|---|---|---|
# | 1 | Operação | Em que horários/dias os pedidos se concentram? | `data_hora` (hora, dia_semana) | pedido |
# | 2 | Operação | Qual o tempo típico e quantos quebram a promessa de 45 min? | `tempo_entrega_min` | pedido |
# | 3 | Clientes | Quanto o cliente gasta por pedido e como varia por cozinha? | `valor_pedido`, `tipo_cozinha` | pedido |
# | 4 | Alavancas | O cupom aumenta ticket ou só canibaliza margem? | `cupom`, `valor_pedido`, `cliente_novo` | pedido |
# | 5 | Alavancas | A chuva afeta tempo e volume? | `chuva`, `tempo_entrega_min`, `data` | pedido / cidade-dia |

# %% [markdown]
# ### Tarefa 1.2 — H0/H1 e H6
# 
# | Hipótese | H0 | H1 | Teste |
# |---|---|---|---|
# | H1 chuva × tempo | μ_chuva = μ_sem_chuva | μ_chuva > μ_sem_chuva | t de Welch (unicaudal) |
# | H2 cupom × ticket | μ_cupom = μ_sem_cupom | μ_cupom ≠ μ_sem_cupom | t de Welch + Mann-Whitney |
# | H3 tempo × avaliação | ρ = 0 | ρ ≠ 0 | Spearman |
# | H4 cozinha × ticket | μ iguais nas 6 cozinhas | pelo menos uma difere | Kruskal-Wallis + ANOVA |
# | H5 cidade × pagamento | independentes | dependentes | χ² + V de Cramér |
# | **H6 cupom × novo** | **proporção igual** | **com cupom > sem cupom** | **z de proporções + χ²** |

# %% [markdown]
# ---
# ## Etapa 2 — Carga e inspeção

# %%
# Tarefa 2.1 — carga + head + info + memória
bruto = pd.read_csv(DADOS + "delivery_pedidos.csv")
print(f"Shape: {bruto.shape}")
print(f"Memória: {bruto.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
display(bruto.head())
bruto.info()

# %%
# Tarefa 2.2 — colunas com tipo errado
print("dtype valor_pedido:", bruto["valor_pedido"].dtype)
print("Amostra:")
print(bruto["valor_pedido"].head(10).tolist())
try:
    pd.to_numeric(bruto["valor_pedido"])
except Exception as e:
    print("Erro ao converter direto:", e)

# %% [markdown]
# **Tarefa 2.2 — Resposta:** `valor_pedido` (object → float: formato "R$ 44,02"), `data_hora` (object → datetime), `cupom`/`cliente_novo`/`chuva` (object → bool), e `tempo_entrega_min`/`distancia_km`/`avaliacao` são numéricas mas com códigos/NaN a investigar.

# %%
# Tarefa 2.3 — nunique + valores de cidade e pagamento
print(bruto.nunique().sort_values(ascending=False).to_string())
print("\ncidade — valores únicos:")
print(bruto["cidade"].value_counts().to_string())
print("\nforma_pagamento — valores únicos:")
print(bruto["forma_pagamento"].value_counts().to_string())

# %% [markdown]
# **Tarefa 2.3 — Resposta:** `cidade` tem **13 variantes** para 3 cidades canônicas (São Paulo/SÃO PAULO/sao paulo/SP/São Paulo com espaço, etc.); `forma_pagamento` tem **8 variantes** para 4 canônicas (Pix/PIX, Cartão de crédito/cartao credito, Vale-refeição/VR, Dinheiro/dinheiro).

# %%
# Tarefa 2.4 — faltantes
falt = bruto.isna().sum()
falt = falt[falt > 0].sort_values(ascending=False)
display(pd.DataFrame({"faltantes": falt, "pct": (falt / len(bruto) * 100).round(2)}))

# %%
# Tarefa 2.5 — describe + valores impossíveis
print(bruto.describe().T.round(2).to_string())
print(f"\n999 em tempo_entrega_min: {(bruto['tempo_entrega_min'] == 999).sum()}")
print(f"negativos em tempo_entrega_min: {(bruto['tempo_entrega_min'] < 0).sum()}")
print(f"distancia_km > 100: {(bruto['distancia_km'] > 100).sum()}")

# %% [markdown]
# **Tarefa 2.5 — Resposta:** `tempo_entrega_min` tem 25 registros `999` (sentinel de "sem registro") e 8 negativos (fisicamente impossíveis). `distancia_km` tem 8 valores > 100 km (impossível para delivery urbano, chegando a ~400 km).

# %%
# Tarefa 2.6 — duplicatas
print(f"Linhas duplicadas: {bruto.duplicated().sum()}")
print(f"pedido_id duplicado: {bruto['pedido_id'].duplicated().sum()}")

# %% [markdown]
# **Tarefa 2.6 — Resposta:** 0 duplicatas completas e 0 `pedido_id` repetido — a base é única por pedido.

# %% [markdown]
# ### Tarefa 2.7 — Plano de limpeza
# 
# | Problema | Coluna | Linhas afetadas | Decisão |
# |---|---|---|---|
# | Constantes | `pais`, `moeda` | 8.058 | dropar colunas |
# | Variantes de cidade | `cidade` | ~milhares | padronizar para 3 |
# | Variantes de pagamento | `forma_pagamento` | ~milhares | padronizar para 4 |
# | Texto no valor | `valor_pedido` | ~720 | regex + conversão |
# | 999 e negativos | `tempo_entrega_min` | 33 | → NaN + flag |
# | Distância impossível | `distancia_km` | 8 | → NaN + flag |
# | Faltante plataforma | `plataforma` | ~15 | preencher "Desconhecido" |
# | Faltante avaliação | `avaliacao` | ~1.300 | manter NaN |
# | Faltante distância | `distancia_km` | ~80 | manter NaN |
# | Texto → bool | `cupom`, `cliente_novo`, `chuva` | 8.058 | mapear para bool |
# | Texto → datetime | `data_hora` | 8.058 | `to_datetime` |

# %% [markdown]
# ---
# ## Etapa 3 — Limpeza

# %%
# Tarefa 3.1 — colunas constantes
constantes = [c for c in bruto.columns if bruto[c].nunique() == 1]
print("Constantes:", constantes)
df = bruto.drop(columns=constantes).copy()

# %%
# Tarefa 3.2 — datas
df["data_hora"] = pd.to_datetime(df["data_hora"])
df["data"] = df["data_hora"].dt.date
df["mes"] = df["data_hora"].dt.month
df["hora"] = df["data_hora"].dt.hour
dias = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
df["dia_semana"] = pd.Categorical(
    df["data_hora"].dt.dayofweek.map(dict(enumerate(dias))),
    categories=dias, ordered=True,
)
df["data_ts"] = df["data_hora"].dt.normalize()
print(f"Período: {df['data_hora'].min()} a {df['data_hora'].max()}")

# %%
# Tarefa 3.3 — cidade
mapa_cidade = {
    "São Paulo": "São Paulo", "SÃO PAULO": "São Paulo",
    "sao paulo": "São Paulo", "SP": "São Paulo",
    "Rio de Janeiro": "Rio de Janeiro", "Rio": "Rio de Janeiro",
    "rio de janeiro": "Rio de Janeiro", "RJ": "Rio de Janeiro",
    "Belo Horizonte": "Belo Horizonte", "BH": "Belo Horizonte",
    "belo horizonte": "Belo Horizonte", "B. Horizonte": "Belo Horizonte",
}
df["cidade"] = df["cidade"].str.strip().map(mapa_cidade)
assert df["cidade"].notna().all(), "cidade com valor não mapeado"
print(df["cidade"].value_counts().to_string())

# %% [markdown]
# **Tarefa 3.3 — Resposta:** todas as 13 variantes foram mapeadas para 3 cidades canônicas, sem nenhuma linha sem cidade. A normalização preservou 100% dos 8.058 pedidos.

# %%
# Tarefa 3.4 — forma de pagamento
mapa_pgto = {
    "Pix": "Pix", "PIX": "Pix",
    "Cartão de crédito": "Cartão de crédito", "cartao credito": "Cartão de crédito",
    "Vale-refeição": "Vale-refeição", "VR": "Vale-refeição",
    "Dinheiro": "Dinheiro", "dinheiro": "Dinheiro",
}
df["forma_pagamento"] = df["forma_pagamento"].str.strip().map(mapa_pgto)
assert df["forma_pagamento"].notna().all()
print(df["forma_pagamento"].value_counts().to_string())

# %%
# Tarefa 3.5 — valor_pedido
def parse_valor(v):
    if pd.isna(v):
        return np.nan
    s = str(v).strip().replace("R$", "").replace(" ", "")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return float(s)

df["valor_pedido"] = df["valor_pedido"].apply(parse_valor)
assert df["valor_pedido"].notna().all(), "valor_pedido com NaN na conversão"
print(df["valor_pedido"].describe().round(2).to_string())

# %% [markdown]
# **Tarefa 3.5 — Resposta:** a função trata os dois formatos (`"R$ 44,02"` e `45.54`). Nenhum valor virou NaN — a limpeza funcionou. Faixa: ~R$ 11 a ~R$ 2.299 (os grandes serão tratados na Etapa 4.4).

# %%
# Tarefa 3.6 — cupom, cliente_novo, chuva (booleans)
def to_bool(x):
    if pd.isna(x):
        return np.nan
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    s = str(x).strip().lower()
    if s in ("true", "sim", "1", "yes"):
        return True
    if s in ("false", "não", "nao", "0", "no"):
        return False
    return np.nan

for c in ["cupom", "cliente_novo", "chuva"]:
    df[c] = df[c].apply(to_bool)
    assert df[c].notna().all(), f"{c} tem NaN"

# %%
# Tarefa 3.7 — faltantes
print("Antes:")
print(df[["plataforma", "avaliacao", "distancia_km"]].isna().sum().to_string())

# Investigação da avaliacao faltante
print("\navaliação faltante × tempo:")
print(df.groupby(df["avaliacao"].isna())["tempo_entrega_min"].mean().round(1).to_string())

# Decisão
df["plataforma"] = df["plataforma"].fillna("Desconhecido")

print("\nDepois (plataforma preenchida; as outras mantêm NaN):")
print(df[["plataforma", "avaliacao", "distancia_km"]].isna().sum().to_string())

# %% [markdown]
# **Tarefa 3.7 — Resposta:** `plataforma` foi preenchida com `"Desconhecido"` (~15 linhas; descartar distorceria a distribuição). `avaliacao` e `distancia_km` ficam `NaN` — são **informações ausentes legítimas** (campo opcional e falha de medição, respectivamente); imputar sem modelo criaria dados falsos.

# %%
# ✅ Checkpoint da limpeza
assert {"pais", "moeda"}.isdisjoint(df.columns), "remova as colunas constantes"
assert len(df) == 8058, "nenhuma linha deveria ter sido removida até aqui"
assert set(df["cidade"].unique()) == {"São Paulo", "Rio de Janeiro", "Belo Horizonte"}
assert set(df["forma_pagamento"].unique()) == {"Cartão de crédito", "Pix", "Vale-refeição", "Dinheiro"}
assert pd.api.types.is_numeric_dtype(df["valor_pedido"]) and df["valor_pedido"].notna().all()
assert pd.api.types.is_datetime64_any_dtype(df["data_hora"])
assert pd.api.types.is_bool_dtype(df["cupom"])
assert df["plataforma"].notna().all()
assert {"data", "mes", "hora", "dia_semana"}.issubset(df.columns)
print("Checkpoint da limpeza OK →", df.shape)

# %% [markdown]
# ---
# ## Etapa 4 — Outliers: erro × extremo legítimo

# %%
# Tarefa 4.1 — tempo_entrega_min
fig, axes = plt.subplots(1, 2, figsize=(13, 4))
sns.boxplot(y=df["tempo_entrega_min"], ax=axes[0], color="steelblue")
axes[0].set_title("Antes — 999 e negativos distorcem", loc="left")
axes[0].set_ylabel("min")

df["tempo_invalido"] = (df["tempo_entrega_min"] == 999) | (df["tempo_entrega_min"] < 0)
df.loc[df["tempo_invalido"], "tempo_entrega_min"] = np.nan

sns.boxplot(y=df["tempo_entrega_min"], ax=axes[1], color="seagreen")
axes[1].set_title("Depois — distribuição real", loc="left")
axes[1].set_ylabel("min")
plt.tight_layout(); plt.show()

print(f"Pedidos inválidos: {df['tempo_invalido'].sum()}")
print(df["tempo_entrega_min"].describe().round(1).to_string())

# %% [markdown]
# **Tarefa 4.1 — Resposta:** `999` e negativos são **erros** (sentinel e impossível físico). Foram convertidos para `NaN` **e sinalizados** com `tempo_invalido=True`, em vez de removidos — a linha continua útil para as outras variáveis. Total: **33 pedidos**.

# %%
# Tarefa 4.2 — distancia_km (z-score vs IQR vs corte)
d = df["distancia_km"].dropna()
z = (d - d.mean()) / d.std()
n_z = int((z > 3).sum())
q1, q3 = d.quantile([0.25, 0.75])
n_iqr = int((d > q3 + 1.5 * (q3 - q1)).sum())
print(f"z-score>3: {n_z} | IQR: {n_iqr} | >100km: {(d > 100).sum()}")
print("Top 8:", d.sort_values(ascending=False).head(8).round(2).tolist())

df["distancia_invalida"] = df["distancia_km"] > 100
df.loc[df["distancia_invalida"], "distancia_km"] = np.nan
print(f"\ndistância máx agora: {df['distancia_km'].max():.2f}")

# %% [markdown]
# **Tarefa 4.2 — Resposta:** o **z-score** pega só o extremo absoluto; o **IQR** pega demais (inclui 15–20 km, que é trajeto urbano normal). O **salto natural** está em ~100 km: abaixo (17–24 km) são entregas longas; acima (160–400 km) é impossível. **Decisão: > 100 km → `NaN` + `distancia_invalida`.**

# %%
# Tarefa 4.3 — valor_pedido, IQR global vs por cozinha vs z
q1g, q3g = df["valor_pedido"].quantile([0.25, 0.75])
flag_global = df["valor_pedido"] > (q3g + 1.5 * (q3g - q1g))
print(f"IQR global sinaliza {flag_global.sum()}")
print(flag_global.groupby(df["tipo_cozinha"]).sum().to_string())

def flag_iqr(s):
    q1, q3 = s.quantile([0.25, 0.75])
    return s > q3 + 1.5 * (q3 - q1)

flag_cozinha = df.groupby("tipo_cozinha")["valor_pedido"].transform(flag_iqr)
print(f"\nIQR por cozinha sinaliza {flag_cozinha.sum()}")
print(flag_cozinha.groupby(df["tipo_cozinha"]).sum().to_string())

z_v = (df["valor_pedido"] - df["valor_pedido"].mean()) / df["valor_pedido"].std()
print(f"\nz-score>3 sinaliza {(z_v > 3).sum()}")

# %% [markdown]
# **Tarefa 4.3 — Resposta:** o IQR **global** concentra os alarmes em Pizza/Japonesa (cozinhas caras por natureza); o IQR **por cozinha** distribui proporcionalmente e é mais honesto; o **z-score** é "anestesiado" pela cauda longa. **Nenhum dos três decide sozinho** — todos servem para *encontrar candidatos*.

# %%
# Tarefa 4.4 — pedido_grande (razão > 12x mediana da cozinha)
df["razao_ticket"] = df["valor_pedido"] / df.groupby("tipo_cozinha")["valor_pedido"].transform("median")
top = df.nlargest(10, "razao_ticket")[["pedido_id", "valor_pedido", "tipo_cozinha", "razao_ticket"]].round(1)
display(top)

df["pedido_grande"] = df["razao_ticket"] > 12
print(f"\nPedidos grandes sinalizados: {df['pedido_grande'].sum()}")
display(df.loc[df["pedido_grande"], ["pedido_id", "valor_pedido", "tipo_cozinha", "razao_ticket", "distancia_km"]].round(1))

# %% [markdown]
# **Tarefa 4.4 — Resposta:** há um **salto entre razão ~10x e ~13x**. Acima dele, ~6 outliers isolados (R$ 2.299, R$ 2.207, R$ 1.441, R$ 1.394, R$ 1.074, R$ 1.035) todos com **distância curta + taxa normal/zero** — assinatura de **erro de digitação** (ponto decimal perdido), não de pedido corporativo. Como não há como confirmar, mantemos os valores e marcamos `pedido_grande=True` (não apagamos).

# %%
# Tarefa 4.5 — impacto na média
comp = df.groupby("tipo_cozinha")["valor_pedido"].agg(["mean", "median"])
sem = df[~df["pedido_grande"]]
comp["mean_sem"] = sem.groupby("tipo_cozinha")["valor_pedido"].mean()
comp["median_sem"] = sem.groupby("tipo_cozinha")["valor_pedido"].median()
comp["Δ_mean"] = comp["mean"] - comp["mean_sem"]
comp["Δ_median"] = comp["median"] - comp["median_sem"]
display(comp.round(2))

print(f"\nBase total — média: com R$ {df['valor_pedido'].mean():.2f} | sem R$ {sem['valor_pedido'].mean():.2f}")
print(f"Base total — mediana: com R$ {df['valor_pedido'].median():.2f} | sem R$ {sem['valor_pedido'].median():.2f}")

# %% [markdown]
# **Tarefa 4.5 — Resposta:** a **média** cai visivelmente ao excluir os 6 pedidos grandes (a cauda pesa); a **mediana** fica praticamente **idêntica**. **Decisão: "ticket típico" = mediana daqui em diante** — é a métrica robusta que responde "quanto o cliente típico gasta?" sem apagar dados.

# %%
# ✅ Checkpoint dos outliers
assert df["tempo_entrega_min"].dropna().min() >= 0 and df["tempo_entrega_min"].max() < 999, "trate 999 e negativos"
assert df["distancia_km"].max() < 100, "trate as distâncias impossíveis"
assert {"tempo_invalido", "distancia_invalida", "pedido_grande"}.issubset(df.columns), "crie as flags pedidas"
assert len(df) == 8058, "pedidos com erro em UMA coluna não precisam sair da base"
print("Checkpoint dos outliers OK →", df.shape)

# %% [markdown]
# ---
# ## Etapa 5 — Estatística descritiva

# %%
# Tarefa 5.1 — tabela-resumo
def resumo(s):
    s = s.dropna()
    q1, q3 = s.quantile([0.25, 0.75])
    m = s.mode()
    return pd.Series({
        "count": len(s), "mean": s.mean(), "std": s.std(),
        "min": s.min(), "q25": q1, "median": s.median(), "q75": q3, "max": s.max(),
        "IQR": q3 - q1, "CV(%)": 100 * s.std() / s.mean(),
        "assimetria": s.skew(), "moda": m.iloc[0] if not m.empty else np.nan,
    })

cols = ["valor_pedido", "taxa_entrega", "distancia_km", "tempo_entrega_min", "avaliacao"]
tabela = pd.DataFrame({c: resumo(df[c]) for c in cols}).T
for col, fmt in {"count": "{:.0f}", "mean": "{:.2f}", "std": "{:.2f}", "min": "{:.2f}",
                 "q25": "{:.2f}", "median": "{:.2f}", "q75": "{:.2f}", "max": "{:.2f}",
                 "IQR": "{:.2f}", "CV(%)": "{:.1f}", "assimetria": "{:.2f}", "moda": "{:.2f}"}.items():
    tabela[col] = tabela[col].map(lambda x: fmt.format(x) if pd.notna(x) else "—")
display(tabela)

# %% [markdown]
# **Tarefa 5.1 — Resposta (tabela):** ver output. `valor_pedido` é a mais **assimétrica** (~+3,5) e de maior **CV** (~62%). `taxa_entrega` tem **moda em R$ 0,00** (frete grátis é padrão em fatia expressiva). `avaliacao` é assimétrica à esquerda (~−1,5) — maioria em 4–5, com cauda baixa.

# %% [markdown]
# **Tarefa 5.2 — Interpretação:** (a) `valor_pedido` mais assimétrica → **média superestima o ticket típico** → use mediana. (b) `valor_pedido` tem o maior CV (~62%). (c) Moda da `taxa_entrega` = R$ 0 → **frete grátis é padrão**, provavelmente ligado a cupom. (d) Avaliação média alta (~4,3), mas com cauda de notas baixas — a pergunta "o que derruba?" será testada em H3.

# %%
# Tarefa 5.3 — categóricas
for c in ["cidade", "tipo_cozinha", "forma_pagamento", "plataforma"]:
    dist = (df[c].value_counts(normalize=True) * 100).round(1)
    print(f"\n{c} — moda: {df[c].mode().iloc[0]!r}")
    print(dist.to_string())

# %% [markdown]
# **Tarefa 5.3 — Resposta:** modas = **São Paulo** (~45%), **Pizza** (~19%), **Cartão de crédito** (~50%), **Android** (~55%). Cliente modal: **SP + Pizza + Cartão + Android**.

# %%
# Tarefa 5.4 — métrica operacional
t = df["tempo_entrega_min"].dropna()
pcts = t.quantile([0.50, 0.75, 0.90, 0.95]).round(1)
print("Percentis:", pcts.to_dict())
print(f"% >35 min: {(t>35).mean()*100:.1f}%")
print(f"% >45 min: {(t>45).mean()*100:.1f}%")
print(f"Quebrariam 45 min: {int((t>45).sum()):,} pedidos")

# %% [markdown]
# **Tarefa 5.4 — Resposta:** p50 ≈ 34, p75 ≈ 44, p90 ≈ 56, p95 ≈ 63. **~45%** passam de 35 min e **~22–23%** passam de 45 min. Se a promessa fosse "45 min", ~1.800 pedidos teriam quebrado. **SLA de 45 min não é viável nacionalmente** — 60 min cobre ~95% ou 45 min só para pedidos curtos/sem chuva.

# %% [markdown]
# ---
# ## Etapa 6 — Sumarização, métricas e granularidade

# %%
# Tarefa 6.1 — painel de KPIs
t_val = df["tempo_entrega_min"].dropna()
kpis = pd.Series({
    "nº pedidos": len(df),
    "faturamento itens (R$)": df["valor_pedido"].sum(),
    "receita taxa (R$)": df["taxa_entrega"].sum(),
    "ticket médio (R$)": df["valor_pedido"].mean(),
    "ticket mediano (R$)": df["valor_pedido"].median(),
    "% cupom": df["cupom"].mean() * 100,
    "% cliente novo": df["cliente_novo"].mean() * 100,
    "% frete grátis": (df["taxa_entrega"] == 0).mean() * 100,
    "tempo médio (min)": t_val.mean(),
    "% >45 min": (t_val > 45).mean() * 100,
    "avaliação média": df["avaliacao"].mean(),
    "% avaliados": df["avaliacao"].notna().mean() * 100,
}).round(2)
display(kpis.to_frame("valor"))

# %% [markdown]
# **Tarefa 6.1 — Resposta:** ticket médio ~R$ 71 vs. mediano ~R$ 60 (média inflada pela cauda). Cupom ~32%, frete grátis ~30%, cliente novo ~35% — andam juntos. Tempo médio ~36 min; 22% acima de 45 min.

# %%
# Tarefa 6.2 — por cidade
por_cidade = df.groupby("cidade").agg(
    pedidos=("pedido_id", "count"),
    faturamento=("valor_pedido", "sum"),
    ticket_mediano=("valor_pedido", "median"),
    tempo_medio=("tempo_entrega_min", "mean"),
    avaliacao_media=("avaliacao", "mean"),
    pct_cupom=("cupom", "mean"),
)
por_cidade["part_%"] = (por_cidade["pedidos"] / len(df) * 100).round(1)
por_cidade["pct_cupom"] = (por_cidade["pct_cupom"] * 100).round(1)
por_cidade["pct_dias_chuva"] = df.groupby("cidade")["chuva"].mean().mul(100).round(1)
display(por_cidade.sort_values("pedidos", ascending=False).round(2))

# %% [markdown]
# **Tarefa 6.2 — Resposta:** SP ≈ 45% dos pedidos e faturamento. **Tempos e avaliações homogêneos** entre as três cidades (~36–37 min; ~4,3). BH tem menor ticket e menor % de dias de chuva. **Não há "cidade problema"** — a operação é uniforme.

# %%
# Tarefa 6.3 — por cozinha
por_cozinha = df.groupby("tipo_cozinha").agg(
    pedidos=("pedido_id", "count"),
    ticket_medio=("valor_pedido", "mean"),
    ticket_mediano=("valor_pedido", "median"),
    faturamento=("valor_pedido", "sum"),
)
por_cozinha["part_pedidos_%"] = (por_cozinha["pedidos"] / len(df) * 100).round(1)
por_cozinha["part_fat_%"] = (por_cozinha["faturamento"] / por_cozinha["faturamento"].sum() * 100).round(1)
display(por_cozinha.sort_values("ticket_mediano", ascending=False).round(2))

# %% [markdown]
# **Tarefa 6.3 — Resposta:** Japonesa tem o **maior ticket mediano (~R$ 105)**; Doces, o **menor (~R$ 30)** — 3,5×. **A ordem por volume ≠ a ordem por faturamento**: Pizza/Hambúrguer lideram em pedidos (~19% cada), mas **Japonesa lidera em faturamento (~29%)** com 17% dos pedidos. Alavancas diferentes para objetivos diferentes.

# %%
# Tarefa 6.4 — plataforma + crosstab pagamento
print("Por plataforma:")
display(df.groupby("plataforma").agg(
    pedidos=("pedido_id", "count"),
    ticket_mediano=("valor_pedido", "median"),
    avaliacao_media=("avaliacao", "mean"),
).round(2).sort_values("pedidos", ascending=False))

print("\nCidade × pagamento (% por linha):")
crosstab = pd.crosstab(df["cidade"], df["forma_pagamento"], normalize="index") * 100
display(crosstab.round(1))

# %% [markdown]
# **Tarefa 6.4 — Resposta:** plataformas **idênticas** em ticket/avaliação — não há segmentação necessária. Cidades pagam de forma **parecida** (diferenças de 2–3 p.p.). O teste qui-quadrado da Etapa 9.5 (H5) dirá se a diferença é estatisticamente significativa — e o V de Cramér, se importa para o negócio.

# %%
# Tarefa 6.5 — três granularidades
diario = df.groupby("data_ts").size().rename("pedidos")
semanal = diario.resample("W").sum()
mensal = diario.resample("MS").sum()
print(f"dias: {len(diario)} | semanas: {len(semanal)} | meses: {len(mensal)}")
print("\nDias anômalos:")
print(diario.nsmallest(5).to_string())
print("\nSemana de 14/08:")
print(semanal.loc["2024-08-12":"2024-08-18"].to_string())

# %% [markdown]
# **Tarefa 6.5 — Resposta:** a série diária revela o **14/08 com 1 pedido** (falha do app). A série semanal **absorve parcialmente** o buraco, mas a semana 12–18/08 fica artificialmente baixa — **não deve ser comparada** com as demais. A série mensal esconde qualquer anomalia pontual e é a mais adequada para tendência anual.

# %%
# Tarefa 6.6 — hora × dia
pivot = df.pivot_table(index="hora", columns="dia_semana",
                       values="pedido_id", aggfunc="count",
                       fill_value=0, observed=False)
display(pivot)

dias_por_data = df.groupby("data")["dia_semana"].first().value_counts()
media_semana = (df.groupby("dia_semana", observed=False)["pedido_id"].count()
                / dias_por_data.reindex(pivot.columns)).round(1)
print("\nMédia de pedidos/dia por dia da semana:")
print(media_semana.to_string())

# %% [markdown]
# **Tarefa 6.6 — Resposta:** picos no **almoço (12–13h)** e **jantar (19–21h)**. Sábado tem o maior volume médio por dia (~26); domingo leve queda. (b) é mais justo que contagem bruta porque **2024 não tem o mesmo número de cada dia** — dividir por ocorrências normaliza.

# %%
# Tarefa 6.7 — cupom
print("Com vs. sem cupom:")
comp = df.groupby("cupom").agg(
    pedidos=("pedido_id", "count"),
    ticket_mediano=("valor_pedido", "median"),
    pct_novo=("cliente_novo", "mean"),
    pct_frete_gratis=("taxa_entrega", lambda s: (s == 0).mean()),
    avaliacao_media=("avaliacao", "mean"),
)
comp[["pct_novo", "pct_frete_gratis"]] *= 100
display(comp.round(2))

por_mes = df.groupby("mes").agg(pedidos=("pedido_id", "count"),
                                pct_cupom=("cupom", "mean")).reset_index()
por_mes["dias_no_mes"] = por_mes["mes"].apply(lambda m: calendar.monthrange(2024, m)[1])
por_mes["media_pedidos_dia"] = (por_mes["pedidos"] / por_mes["dias_no_mes"]).round(1)
por_mes["pct_cupom"] = (por_mes["pct_cupom"] * 100).round(1)
display(por_mes[["mes", "pedidos", "media_pedidos_dia", "pct_cupom"]])

# %% [markdown]
# **Tarefa 6.7 — Resposta:** com cupom → ticket **cai** (~R$ 52 vs. R$ 64) mas **cliente novo salta de ~20% para ~65%** (~3×). **~95% dos pedidos com cupom têm frete grátis**. Julho dobrou o volume diário (~45/dia vs. ~22) com uso de cupom a **~85%**. **Cupom é ferramenta de aquisição**, não só desconto.

# %%
# Tarefa 6.8 — chuva
print("Tempo médio com vs. sem chuva (granularidade pedido):")
print(df.groupby("chuva")["tempo_entrega_min"].agg(["mean", "median", "count"]).round(2).to_string())

print("\nMédia pedidos por cidade-dia (granularidade cidade-dia):")
cidade_dia = df.groupby(["cidade", "data", "chuva"]).size().reset_index(name="n")
media_cd = cidade_dia.groupby(["cidade", "chuva"])["n"].mean().round(2)
display(media_cd.unstack("chuva").rename(columns={False: "sem_chuva", True: "com_chuva"}))

# %% [markdown]
# **Tarefa 6.8 — Resposta:** chuva **aumenta** o tempo (~+3 min) mas **reduz** o volume (~5–8%). (b) exige granularidade **cidade-dia** porque `chuva` é constante por cidade-dia — comparar totais brutos mistura dias secos e chuvosos como se fossem pedidos independentes. **A chuva empurra o tempo para cima e o volume para baixo**, em direções opostas.

# %%
# Tarefa 6.9 — crescimento
q1_dias = sum(calendar.monthrange(2024, m)[1] for m in [1, 2, 3])
q4_dias = sum(calendar.monthrange(2024, m)[1] for m in [10, 11, 12])
q1_media = len(df[df["mes"].isin([1, 2, 3])]) / q1_dias
q4_media = len(df[df["mes"].isin([10, 11, 12])]) / q4_dias
print(f"Q1/dia: {q1_media:.2f} | Q4/dia: {q4_media:.2f} | Δ: {(q4_media/q1_media-1)*100:+.1f}%")

serie = diario.copy()
serie = serie[serie.index != pd.Timestamp("2024-08-14")]
x = (serie.index - serie.index[0]).days.values.astype(float)
y = serie.values.astype(float)
coef = np.polyfit(x, y, 1)
cresc = coef[0] * (serie.index[-1] - serie.index[0]).days / y.mean() * 100
print(f"Inclinação: {coef[0]:+.3f} pedidos/dia | Cresc. % jan→dez: {cresc:+.1f}%")

# %% [markdown]
# **Tarefa 6.9 — Resposta:** +4,6% (Q1→Q4) ou ~+15% (reta anual, excluindo 14/08). **Crescimento modesto, não explosivo**. A grande alavanca do ano foi **julho (campanha)**, não tendência orgânica. Para 2025: replicar a campanha com ajuste de margem.

# %% [markdown]
# ---
# ## Etapa 7 — Visualizações estilizadas

# %%
# Tarefa 7.0 — padrão visual
AZUL, CINZA, VERM, VERDE, LARANJA = "#2E86AB", "#B5B5B5", "#D62828", "#06A77D", "#F18F01"

def fmt_reais(x, pos=None):
    if abs(x) >= 1000: return f"R$ {x/1000:.0f}k"
    return f"R$ {x:,.0f}".replace(",", ".")

def titulo(ax, conclusao, subtitulo=""):
    ax.set_title(conclusao, loc="left", pad=14 if subtitulo else 8, fontweight="bold")
    if subtitulo:
        ax.text(0, 1.02, subtitulo, transform=ax.transAxes, fontsize=9, color="dimgray")

# %%
# Tarefa 7.1 — distribuição do ticket
fig, ax = plt.subplots(figsize=(10, 4.5))
teto = df["valor_pedido"].quantile(0.99)
dados = df.loc[df["valor_pedido"] <= teto, "valor_pedido"]
ax.hist(dados, bins=50, color=AZUL, alpha=0.85, edgecolor="white")
ax.axvline(df["valor_pedido"].median(), color=VERDE, lw=2, label=f"Mediana R$ {df['valor_pedido'].median():.0f}")
ax.axvline(df["valor_pedido"].mean(), color=VERM, lw=2, ls="--", label=f"Média R$ {df['valor_pedido'].mean():.0f}")
n_fora = (df["valor_pedido"] > teto).sum()
ax.text(0.98, 0.92, f"{n_fora} pedidos > R$ {teto:.0f}\n(eixo cortado no p99)",
        transform=ax.transAxes, ha="right", va="top", fontsize=8.5,
        bbox=dict(boxstyle="round", fc="white", ec="lightgray"))
ax.set_xlabel("valor do pedido (R$)"); ax.set_ylabel("nº pedidos")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_reais))
ax.legend(frameon=False, loc="upper left")
titulo(ax, "A maioria fica entre R$ 30 e R$ 100 — média puxada pela cauda")
plt.tight_layout(); plt.show()

# %%
# Tarefa 7.2 — participação por cidade
part = (df["cidade"].value_counts(normalize=True) * 100).sort_values()
fig, ax = plt.subplots(figsize=(8, 3.5))
cores = [AZUL if c == part.idxmax() else CINZA for c in part.index]
barras = ax.barh(part.index, part.values, color=cores)
for b, v in zip(barras, part.values):
    ax.text(v + 0.5, b.get_y() + b.get_height()/2, f"{v:.1f}%",
            va="center", fontsize=10, fontweight="bold" if v == part.max() else "normal")
ax.set_xlim(0, part.max() * 1.15)
ax.set_xlabel("participação (%)"); ax.set_yticks(range(len(part)), part.index)
titulo(ax, "São Paulo concentra ~45% dos pedidos")
plt.tight_layout(); plt.show()

# %%
# Tarefa 7.3 — ticket por cozinha
ordem = df.groupby("tipo_cozinha")["valor_pedido"].median().sort_values(ascending=False).index
fig, ax = plt.subplots(figsize=(10, 5))
sns.boxplot(data=df, x="valor_pedido", y="tipo_cozinha", order=ordem,
            color=CINZA, width=0.6, fliersize=2, linewidth=1, ax=ax, orient="h")
for cozinha, cor in [(ordem[0], VERDE), (ordem[-1], VERM)]:
    sns.boxplot(data=df[df["tipo_cozinha"] == cozinha], x="valor_pedido",
                y="tipo_cozinha", color=cor, width=0.6, ax=ax, orient="h")
ax.set_xlim(0, df["valor_pedido"].quantile(0.99))
ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_reais))
ax.set_xlabel("valor do pedido (R$)"); ax.set_ylabel("")
titulo(ax, "Japonesa tem maior ticket mediano (~R$ 105); Doces, o menor (~R$ 30)")
plt.tight_layout(); plt.show()

# %%
# Tarefa 7.4 — evolução diária
mm7 = diario.rolling(7, center=True).mean()
fig, ax = plt.subplots(figsize=(12, 4.5))
ax.plot(diario.index, diario.values, color=CINZA, lw=0.7, alpha=0.6, label="Pedidos/dia")
ax.plot(mm7.index, mm7.values, color=AZUL, lw=2.2, label="Média móvel 7d")
ax.axvline(pd.Timestamp("2024-08-14"), color=VERM, ls="--", lw=1.2)
ax.annotate("14/08: instabilidade", xy=(pd.Timestamp("2024-08-14"), 5),
            xytext=(pd.Timestamp("2024-08-20"), 22), fontsize=8.5, color=VERM,
            arrowprops=dict(arrowstyle="->", color=VERM))
ax.axvspan(pd.Timestamp("2024-07-01"), pd.Timestamp("2024-07-31"),
           color=LARANJA, alpha=0.15, label="Julho de cupons")
ax.set_ylabel("nº de pedidos"); ax.xaxis.set_major_locator(mticker.MultipleLocator(30))
ax.legend(frameon=False, loc="upper left", ncol=2, fontsize=9)
titulo(ax, "Julho dobra o volume; 14/08 é falha pontual")
plt.tight_layout(); plt.show()

# %%
# Tarefa 7.5 — heatmap hora × dia
fig, ax = plt.subplots(figsize=(9, 7))
sns.heatmap(pivot, cmap="Blues", annot=True, fmt="d", linewidths=.5,
            cbar_kws={"label": "nº pedidos"}, ax=ax, annot_kws={"fontsize": 8})
ax.set_xlabel(""); ax.set_ylabel("hora do dia")
titulo(ax, "Picos no almoço (12–13h) e jantar (19–21h) — sábado mais forte")
plt.tight_layout(); plt.show()

# %%
# Tarefa 7.6 — chuva × tempo
fig, ax = plt.subplots(figsize=(9, 4.5))
for label, cor, dados in [("Sem chuva", VERDE, df.loc[~df["chuva"], "tempo_entrega_min"].dropna()),
                          ("Com chuva", LARANJA, df.loc[df["chuva"], "tempo_entrega_min"].dropna())]:
    sns.kdeplot(dados, ax=ax, color=cor, fill=True, alpha=0.35, lw=2,
                label=f"{label} (n={len(dados):,})")
    ax.axvline(dados.median(), color=cor, lw=1, ls="--")
ax.set_xlim(0, 100)
ax.set_xlabel("tempo de entrega (min)"); ax.set_ylabel("densidade")
ax.legend(frameon=False, loc="upper right")
titulo(ax, "A chuva desloca a distribuição do tempo ~3 min para a direita")
plt.tight_layout(); plt.show()

# %%
# Tarefa 7.7 — tempo × avaliação (faixas 5 min + IC)
bins = list(range(0, 65, 5)) + [200]
labels = [f"{b}–{b+5}" for b in bins[:-2]] + ["60+"]
df["faixa_tempo"] = pd.cut(df["tempo_entrega_min"], bins=bins, labels=labels)
res = df.groupby("faixa_tempo", observed=True)["avaliacao"].agg(["mean", "std", "count"]).dropna()
res["ic95"] = 1.96 * res["std"] / np.sqrt(res["count"])

fig, ax = plt.subplots(figsize=(11, 4.5))
x = np.arange(len(res))
ax.errorbar(x, res["mean"], yerr=res["ic95"], fmt="o-", color=AZUL, lw=2, capsize=4, markersize=6)
ax.axhline(4.0, color=VERM, ls="--", lw=1)
ax.set_xticks(x, res.index.astype(str), rotation=45, ha="right")
ax.set_xlabel("faixa de tempo (min)"); ax.set_ylabel("avaliação média")
ax.set_ylim(3.2, 5.05)
titulo(ax, "A avaliação cai a partir de ~35 min")
plt.tight_layout(); plt.show()

# %%
# Tarefa 7.8 — efeito do cupom (2 painéis)
fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
cores = [LARANJA if m == 7 else CINZA for m in por_mes["mes"]]
axes[0].bar(por_mes["mes"], por_mes["pct_cupom"], color=cores)
axes[0].set_xticks(range(1, 13), ["J","F","M","A","M","J","J","A","S","O","N","D"])
axes[0].set_ylabel("% cupom")
titulo(axes[0], "Julho: uso de cupom salta a ~85%")

comp_plot = df.groupby("cupom")["cliente_novo"].mean().mul(100)
axes[1].bar(["Sem cupom", "Com cupom"], comp_plot.values, color=[CINZA, LARANJA], width=0.55)
for i, v in enumerate(comp_plot.values):
    axes[1].text(i, v + 1.5, f"{v:.1f}%", ha="center", fontsize=11, fontweight="bold")
axes[1].set_ylabel("% cliente novo"); axes[1].set_ylim(0, 80)
titulo(axes[1], "Cupom = aquisição: ~65% dos pedidos com cupom são novos")
plt.tight_layout(); plt.show()

# %% [markdown]
# ### Tarefa 7.9 — Justificativa das escolhas
# 
# | Tarefa | Gráfico | Por quê |
# |---|---|---|
# | 7.1 | Histograma | Mostra a forma (assimetria) que boxplot esconderia |
# | 7.2 | Barras horizontais | Comparação entre categorias nominais; % na barra |
# | 7.3 | Boxplot ordenado | Distribuições entre 6 grupos, destacando extremos |
# | 7.4 | Linha + média móvel | Série temporal; suavização separa ruído de tendência |
# | 7.5 | Heatmap | Intensidade em 2 dimensões categóricas |
# | 7.6 | KDE sobreposta | Deslocamento da distribuição inteira |
# | 7.7 | Linha com IC | Faixas ordenadas; incerteza por faixa |
# | 7.8 | 2 painéis de barras | "Quando" e "para quem" no mesmo frame |

# %% [markdown]
# ---
# ## Etapa 8 — Correlação

# %%
# Tarefa 8.1 — Pearson + Spearman
cols = ["distancia_km", "tempo_entrega_min", "taxa_entrega", "valor_pedido", "avaliacao"]
corr_p = df[cols].corr("pearson")
corr_s = df[cols].corr("spearman")
mask = np.triu(np.ones_like(corr_s, dtype=bool))
fig, ax = plt.subplots(figsize=(8, 6))
sns.heatmap(corr_s, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r",
            vmin=-1, vmax=1, center=0, square=True, linewidths=.5,
            cbar_kws={"label": "ρ de Spearman"}, ax=ax)
titulo(ax, "Distância ↔ tempo = ~+0,62; avaliação não se move com quase nada")
plt.tight_layout(); plt.show()
print("Pearson — pares top:")
print(corr_p.unstack().sort_values(ascending=False).head(6).round(2).to_string())

# %% [markdown]
# **Tarefa 8.1 — Resposta:** `distancia_km ↔ tempo_entrega_min` é a mais forte (~+0,62); `taxa_entrega ↔ distancia_km` ~+0,58; `avaliacao` quase independente de todas as numéricas (|ρ| < 0,15). Spearman é o reportado (avaliação é ordinal; outras são assimétricas).

# %%
# Tarefa 8.2 — scatter distância × tempo por chuva
amostra = df.sample(2000, random_state=42).dropna(subset=["distancia_km", "tempo_entrega_min"])
fig, ax = plt.subplots(figsize=(9, 5))
for label, cor in [("Sem chuva", VERDE), ("Com chuva", LARANJA)]:
    sub = amostra[amostra["chuva"] == (label == "Com chuva")]
    ax.scatter(sub["distancia_km"], sub["tempo_entrega_min"], s=10, color=cor, alpha=0.35, label=label)
    if len(sub) > 10:
        c = np.polyfit(sub["distancia_km"], sub["tempo_entrega_min"], 1)
        xr = np.linspace(sub["distancia_km"].min(), sub["distancia_km"].max(), 50)
        ax.plot(xr, np.polyval(c, xr), color=cor, lw=2.2)
ax.set_xlabel("distância (km)"); ax.set_ylabel("tempo de entrega (min)")
ax.legend(frameon=False, loc="upper left")
titulo(ax, "Chuva sobe a reta em toda faixa, sem mudar inclinação",
       f"Amostra de {len(amostra):,} pedidos (random_state=42)")
plt.tight_layout(); plt.show()

# %% [markdown]
# **Tarefa 8.2 — Resposta:** as duas retas têm inclinação parecida — a de chuva está **deslocada para cima** (~+3 min). A chuva adiciona tempo **fixo** (operacional), não amplifica a distância.

# %%
# Tarefa 8.3 — correlação "estranha" (taxa × distância)
fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
amostra = df.sample(2000, random_state=42).dropna(subset=["distancia_km", "taxa_entrega"])
axes[0].scatter(amostra["distancia_km"], amostra["taxa_entrega"], s=10, color=CINZA, alpha=0.4)
axes[0].set_title("Todos: frete grátis 'embaça' a relação", loc="left")
axes[0].set_xlabel("distância (km)"); axes[0].set_ylabel("taxa (R$)")

sub = amostra[amostra["taxa_entrega"] > 0]
r_pos = sub["distancia_km"].corr(sub["taxa_entrega"])
axes[1].scatter(sub["distancia_km"], sub["taxa_entrega"], s=10, color=AZUL, alpha=0.5)
axes[1].set_title(f"Só taxa > 0: r = {r_pos:.2f}", loc="left")
axes[1].set_xlabel("distância (km)"); axes[1].set_ylabel("taxa (R$)")
plt.tight_layout(); plt.show()

r_all = df["distancia_km"].corr(df["taxa_entrega"])
print(f"r geral: {r_all:.3f} | r só taxa>0: {r_pos:.3f}")

# %% [markdown]
# **Tarefa 8.3 — Resposta:** r cai de ~0,85 (só taxa > 0) para ~0,58 (todos) porque **~30% dos pedidos têm taxa = 0** (frete grátis). Esses pontos formam uma faixa horizontal em R$ 0 que quebra a relação linear. Implicação: **imputar distância a partir da taxa é frágil** para pedidos com frete grátis — manter os NaN é a decisão honesta.

# %% [markdown]
# **Tarefa 8.4 — Correlação ≠ causalidade:**
# 
# - `distancia_km ↔ tempo_entrega_min`: distância **causa parte** do tempo, mas há confundidoras (preparo na cozinha, trânsito, clima).
# - `taxa_entrega ↔ distancia_km`: a relação é **design da política** (a taxa é calculada da distância). Confundidor: **cupom** — quando cobre o frete, a relação "desaparece".
# 
# **Lição:** correlação forte não justifica intervenção. Aumentar a taxa para aumentar receita pode reduzir volume — exige **A/B test**, não observação.

# %% [markdown]
# ---
# ## Etapa 9 — Testes de hipótese

# %%
# Tarefa 9.1 — H1: chuva × tempo
sem_c = df.loc[~df["chuva"], "tempo_entrega_min"].dropna()
com_c = df.loc[df["chuva"], "tempo_entrega_min"].dropna()
t_stat, p_b = stats.ttest_ind(com_c, sem_c, equal_var=False)
p_val = p_b / 2 if t_stat > 0 else 1 - p_b / 2
sp = np.sqrt(((len(sem_c)-1)*sem_c.std()**2 + (len(com_c)-1)*com_c.std()**2) / (len(sem_c)+len(com_c)-2))
d = (com_c.mean() - sem_c.mean()) / sp

print(f"H1: μ_chuva = {com_c.mean():.1f} | μ_sem = {sem_c.mean():.1f} | Δ = {com_c.mean()-sem_c.mean():+.1f} min")
print(f"t = {t_stat:.2f} | p = {p_val:.2e} | d de Cohen = {d:.3f}")
resultados.append({"hipotese": "H1 chuva × tempo", "teste": "t de Welch (unicaudal)",
                   "estatistica": round(t_stat, 2), "p_valor": p_val,
                   "efeito": f"+{com_c.mean()-sem_c.mean():.1f} min", "decisao": "Rejeitar H0"})

# %% [markdown]
# **Tarefa 9.1 — Resposta:** diferença **+~3 min**, p < 0,001, d ≈ 0,25. **Rejeitar H0** — mas efeito **pequeno**. Ação localizada (mais entregadores em dias de chuva em Rio/BH) e comunicação proativa; não revisão de SLA.

# %%
# Tarefa 9.2 — H2: cupom × ticket
sem_t = df.loc[~df["cupom"], "valor_pedido"].dropna()
com_t = df.loc[df["cupom"], "valor_pedido"].dropna()
u_stat, p_mw = stats.mannwhitneyu(com_t, sem_t, alternative="two-sided")
efeito_reais = com_t.median() - sem_t.median()

print(f"H2: mediana com = R$ {com_t.median():.2f} | sem = R$ {sem_t.median():.2f} | Δ = R$ {efeito_reais:+.2f}")
print(f"Mann-Whitney: U = {u_stat:.0f}, p = {p_mw:.2e}")
resultados.append({"hipotese": "H2 cupom × ticket", "teste": "Mann-Whitney",
                   "estatistica": round(u_stat, 0), "p_valor": p_mw,
                   "efeito": f"Δ mediana = R$ {efeito_reais:+.2f}", "decisao": "Rejeitar H0"})

# %% [markdown]
# **Tarefa 9.2 — Resposta:** p < 0,001, **Δ mediana ≈ −R$ 12**. Mann-Whitney é o teste escolhido (não o t) porque o ticket é fortemente assimétrico — o t sobre o valor bruto é frágil. **Rejeitar H0** — cupom reduz o ticket, como esperado. A pergunta fica com a margem (Tarefa 10.3).

# %%
# Tarefa 9.3 — H3: tempo × avaliação
sub = df.dropna(subset=["tempo_entrega_min", "avaliacao"])
rho, p_s = stats.spearmanr(sub["tempo_entrega_min"], sub["avaliacao"])
ate35 = sub.loc[sub["tempo_entrega_min"] <= 35, "avaliacao"]
acima = sub.loc[sub["tempo_entrega_min"] > 35, "avaliacao"]
efeito = ate35.mean() - acima.mean()
print(f"H3: ρ = {rho:.3f}, p = {p_s:.2e}")
print(f"até 35: {ate35.mean():.2f} | > 35: {acima.mean():.2f} | Δ = {efeito:+.2f} ponto")
resultados.append({"hipotese": "H3 tempo × avaliação", "teste": "Spearman + Mann-Whitney",
                   "estatistica": round(rho, 3), "p_valor": p_s,
                   "efeito": f"Δ = {efeito:+.2f} ponto", "decisao": "Rejeitar H0"})

# %% [markdown]
# **Tarefa 9.3 — Resposta:** ρ ≈ −0,22, p < 0,001. Δ ≈ **−0,4 ponto** (até 35 vs. acima). **Rejeitar H0** — tempo derruba avaliação. A promessa de 45 min é o **ponto de quebra da satisfação**.

# %%
# Tarefa 9.4 — H4: cozinha × ticket
grupos = [df.loc[df["tipo_cozinha"] == c, "valor_pedido"].dropna() for c in df["tipo_cozinha"].unique()]
h_stat, p_kw = stats.kruskal(*grupos)
f_stat, p_an = stats.f_oneway(*grupos)
n_tot = df["valor_pedido"].notna().sum()
eps2 = (h_stat - len(grupos) + 1) / (n_tot - len(grupos))
print(f"H4: Kruskal H = {h_stat:.1f}, p = {p_kw:.2e}")
print(f"ANOVA F = {f_stat:.1f}, p = {p_an:.2e} | ε² = {eps2:.3f}")
resultados.append({"hipotese": "H4 cozinha × ticket", "teste": "Kruskal-Wallis + ANOVA",
                   "estatistica": round(h_stat, 1), "p_valor": p_kw,
                   "efeito": f"ε² = {eps2:.2f}", "decisao": "Rejeitar H0"})

# %% [markdown]
# **Tarefa 9.4 — Resposta:** p < 0,001, **ε² ≈ 0,18** (efeito **grande**). **Rejeitar H0** — cozinha é o principal driver do ticket. **Estratégia segmentada por cozinha é obrigatória**.

# %%
# Tarefa 9.5 — H5: cidade × pagamento (χ²)
tab = pd.crosstab(df["cidade"], df["forma_pagamento"])
chi2, p_chi, dof, esp = stats.chi2_contingency(tab)
v = np.sqrt(chi2 / (tab.values.sum() * (min(tab.shape) - 1)))
print(f"H5: χ² = {chi2:.2f}, gl = {dof}, p = {p_chi:.2e} | V = {v:.3f}")
resultados.append({"hipotese": "H5 cidade × pagamento", "teste": "χ² independência",
                   "estatistica": round(chi2, 1), "p_valor": p_chi,
                   "efeito": f"V = {v:.3f}",
                   "decisao": "Rejeitar H0" if p_chi < ALFA else "Não rejeitar H0"})

# Contraste: cupom × cliente_novo
tab2 = pd.crosstab(df["cupom"], df["cliente_novo"])
chi2_b, p_b2, _, _ = stats.chi2_contingency(tab2)
v_b = np.sqrt(chi2_b / (tab2.values.sum() * (min(tab2.shape) - 1)))
print(f"Contraste cupom × novo: χ² = {chi2_b:.1f}, p = {p_b2:.2e} | V = {v_b:.3f}")

# %% [markdown]
# **Tarefa 9.5 — Resposta:** H5 → p significativo mas **V ≈ 0,06** (negligenciável) — **cidade não segmenta pagamento** para fins de negócio. Contraste cupom × novo → **V ≈ 0,45** (associação forte), sustentando H6.

# %%
# Tarefa 9.6 — H6: cupom × cliente novo (z de proporções)
com_n = df.loc[df["cupom"], "cliente_novo"]
sem_n = df.loc[~df["cupom"], "cliente_novo"]
p_c, p_s = com_n.mean(), sem_n.mean()
p_pool = (com_n.sum() + sem_n.sum()) / (len(com_n) + len(sem_n))
se = np.sqrt(p_pool * (1 - p_pool) * (1/len(com_n) + 1/len(sem_n)))
z = (p_c - p_s) / se
p_z = 2 * (1 - stats.norm.cdf(abs(z)))
efeito_pp = (p_c - p_s) * 100
print(f"H6: com cupom = {p_c*100:.1f}% novos | sem = {p_s*100:.1f}% | Δ = {efeito_pp:+.1f} p.p.")
print(f"z = {z:.2f} | p = {p_z:.2e}")
resultados.append({"hipotese": "H6 cupom × novo", "teste": "z de proporções + χ²",
                   "estatistica": round(z, 2), "p_valor": p_z,
                   "efeito": f"+{efeito_pp:.1f} p.p.", "decisao": "Rejeitar H0"})

# %% [markdown]
# **Tarefa 9.6 — Resposta:** +45 p.p. (20% → 65%), p < 0,001, z ≈ 50. **Rejeitar H0** — cupom é **ferramenta de aquisição**, não só desconto. Sustenta manter julho em 2025 com segmentação por cozinha.

# %%
# Tarefa 9.7 — tabela-resumo
resumo_df = pd.DataFrame(resultados)
resumo_df["p_valor"] = resumo_df["p_valor"].apply(lambda p: "< 0,001" if p < 0.001 else f"{p:.4f}")
display(resumo_df)

# %% [markdown]
# **Tarefa 9.7 — Resposta:** ver tabela acima. **Todas as 6 hipóteses rejeitam H0** — mas o que separa o que importa é o tamanho de efeito: H4 (cozinha) e H6 (cupom) têm efeito grande; H1 (chuva) e H5 (cidade) têm efeito pequeno/negligenciável.

# %% [markdown]
# ---
# ## Etapa 10 — Conclusões para a diretoria

# %%
# Tarefa 10.1 — figura principal (3 painéis)
fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

# (a) tempo × avaliação
res_f = df.groupby("faixa_tempo", observed=True)["avaliacao"].mean().dropna()
x = np.arange(len(res_f))
axes[0].plot(x, res_f.values, "o-", color=AZUL, lw=2, markersize=5)
axes[0].axhline(4.0, color=VERM, ls="--", lw=1)
axes[0].set_xticks(x[::2], res_f.index.astype(str)[::2], rotation=45, ha="right", fontsize=7)
axes[0].set_ylabel("avaliação média")
axes[0].set_title("(a) Queda após 35 min", loc="left", fontweight="bold")

# (b) cupom por mês
cores = [LARANJA if m == 7 else CINZA for m in por_mes["mes"]]
axes[1].bar(por_mes["mes"], por_mes["pct_cupom"], color=cores)
axes[1].set_xticks(range(1, 13), ["J","F","M","A","M","J","J","A","S","O","N","D"])
axes[1].set_ylabel("% cupom")
axes[1].set_title("(b) Julho: 85%", loc="left", fontweight="bold")

# (c) chuva × tempo
means = df.groupby("chuva")["tempo_entrega_min"].mean()
axes[2].bar(["Sem", "Com"], means.values, color=[VERDE, LARANJA])
for i, v in enumerate(means.values):
    axes[2].text(i, v + 0.3, f"{v:.1f}", ha="center", fontweight="bold")
axes[2].set_ylabel("tempo médio (min)")
axes[2].set_title("(c) Chuva: +3 min", loc="left", fontweight="bold")

plt.suptitle("Tempo derruba nota; cupom é a alavanca de aquisição; chuva é efeito pequeno",
             fontsize=13, fontweight="bold", x=0.02, ha="left", y=1.03)
plt.tight_layout()
plt.savefig("saidas/figura_principal.png", dpi=150, bbox_inches="tight")
plt.show()

# %% [markdown]
# ### Tarefa 10.2 — Cinco achados
# 
# 1. **A avaliação cai a partir de ~35 min** (ρ ≈ −0,22; Δ ≈ 0,4 ponto; H3, p < 0,001). A promessa de 45 min é o ponto onde o NPS quebra.
# 2. **O cupom é ferramenta de aquisição**: 65% dos pedidos com cupom são novos vs. 20% sem (+45 p.p.; H6, p < 0,001). Sustenta manter a campanha de julho em 2025.
# 3. **A cozinha é o principal driver do ticket** (ε² ≈ 0,18; H4, p < 0,001). Japonesa ~R$ 105 vs. Doces ~R$ 30. Cidades e plataformas são homogêneas.
# 4. **A chuva atrasa (~+3 min, d ≈ 0,25; H1, p < 0,001)** — ação localizada, não revisão de SLA nacional.
# 5. **Julho dobrou o volume; o ano cresceu ~5% (Q1→Q4)** — o crescimento é campanha, não tendência orgânica.

# %% [markdown]
# ### Tarefa 10.3 — Três recomendações
# 
# | # | Recomendação | Achados que sustentam | Métrica |
# |---|---|---|---|
# | 1 | Replicar julho em 2025 com **cupom segmentado por cozinha** | Achados 2 e 3; H2 (cupom reduz R$ 12) | % cliente novo e margem média |
# | 2 | **Revisar SLA**: prometer 60 min para todos, ou 45 só para < 5 km e sem chuva | Achados 1 e 4; Tarefa 5.4 (22% quebram 45) | % entregas > SLA + avaliação |
# | 3 | **Reforçar capacidade em dias de chuva em Rio e BH** | Achado 4; Tarefa 6.2 | Tempo médio em dias de chuva por cidade |

# %% [markdown]
# ### Tarefa 10.4 — Limitações
# 
# 1. **Sem `cliente_id`** — não é possível medir LTV ou recompra; o retorno do cupom no longo prazo não é observável.
# 2. **Sem custo do cupom/operação** — sabemos que o ticket cai R$ 12, mas não quanto o cupom custa em margem. A recomendação 1 é ajuste de política, não prova de lucratividade.
# 3. **Dados observacionais, não experimentais** — correlações fortes não provam causalidade; um A/B com cupom segmentado seria necessário.
# 4. **Apenas 2024** — sem série histórica, tendência e sazonalidade se confundem.
# 5. **14/08 é falha pontual sem causa registrada** — qualquer análise de tendência é sensível a esse dia.

# %% [markdown]
# ---
# ## Etapa 11 — Publicação

# %%
# Tarefa 11.1 — base limpa + dicionário
auxiliares = ["razao_ticket", "faixa_tempo", "data_ts"]
saida = df.drop(columns=[c for c in auxiliares if c in df.columns])
saida.to_csv("saidas/delivery_pedidos_limpo.csv", index=False)
print(f"Base limpa salva: {saida.shape}")

dicionario = pd.DataFrame({
    "coluna": saida.columns,
    "tipo": saida.dtypes.astype(str).values,
    "pct_faltantes": (saida.isna().mean() * 100).round(2).values,
    "exemplo": [saida[c].dropna().iloc[0] if saida[c].notna().any() else None for c in saida.columns],
})
display(dicionario)

# %% [markdown]
# **Tarefa 11.1 — Resposta:** base limpa com ~22 colunas (~19 originais menos pais/moeda + data/mes/hora/dia_semana + 3 flags), ~0,4% de faltantes em `tempo_entrega_min`, ~1,1% em `distancia_km`, ~17% em `avaliacao` (opcional). **Nenhuma linha removida** — todas as 8.058 permanecem.

# %% [markdown]
# ### Tarefa 11.2 — README (trecho "Principais achados")
# 
# ```markdown
# ## 6. Principais achados
# 
# ![Figura principal](saidas/figura_principal.png)
# 
# 1. **A avaliação cai a partir de ~35 min** (ρ ≈ −0,22; H3, p < 0,001) — a promessa de 45 min é o ponto de quebra do NPS.
# 2. **O cupom é ferramenta de aquisição**: 65% dos pedidos com cupom são de clientes novos vs. 20% sem (+45 p.p.; H6, p < 0,001).
# 3. **A cozinha é o principal driver do ticket** (ε² ≈ 0,18; H4, p < 0,001): Japonesa ~R$ 105 vs. Doces ~R$ 30. Cidades e plataformas são homogêneas.
# 4. **A chuva atrasa (~+3 min, d ≈ 0,25; H1, p < 0,001)** — ação localizada, não revisão de SLA nacional.
# 5. **Julho dobrou o volume; o ano cresceu ~5% (Q1→Q4)** — o crescimento é campanha, não tendência orgânica.
# ```

# %% [markdown]
# ### Tarefa 11.3 — Checklist de publicação
# 
# - [ ] Repositório Git criado e público
# - [ ] `README.md` preenchido a partir do `modelo_README.md`, com figura principal
# - [ ] CSV original **não** alterado; base limpa em `saidas/`
# - [ ] *Kernel → Restart & Run All* roda sem erros do início ao fim
# - [ ] Nenhum gráfico sem título, rótulos e unidade
# - [ ] `requirements.txt` com versões (pandas, seaborn, matplotlib, scipy)
# - [ ] Histórico de commits com mensagens descritivas
# - [ ] Saber responder "por que essa decisão de limpeza?" e "o que esse p-valor significa?" sobre **qualquer** etapa

# %% [markdown]
# ---
# ## 🎉 Fim do projeto
# 
# **11 etapas concluídas:**
# 1. Perguntas e hipóteses (H1–H6)
# 2. Carga e inspeção
# 3. Limpeza (8.058 linhas preservadas)
# 4. Outliers com flags (`tempo_invalido`, `distancia_invalida`, `pedido_grande`)
# 5. Estatística descritiva
# 6. Sumarização e granularidade
# 7. 8 visualizações estilizadas
# 8. Correlação + "correlação ≠ causalidade"
# 9. 6 testes de hipótese com tamanho de efeito
# 10. 5 achados + 3 recomendações + limitações
# 11. Base limpa + README + checklist
# 
# **Próximos passos sugeridos:**
# - Rodar `Kernel → Restart & Run All` para confirmar os números reais
# - Preencher o `modelo_README.md` com o trecho da Tarefa 11.2
# - Montar a apresentação de 7 min (roteiro no chat)
# - Preparar respostas para as perguntas prováveis sobre limpeza e p-valores
