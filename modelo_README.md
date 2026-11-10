# [Título que diz o resultado, não o tema — ex.: "Chuva e horário de pico atrasam as entregas e derrubam a avaliação: diagnóstico de 2024 do app de delivery"]

> [Uma frase de resumo para quem só vai ler esta linha: qual é a principal conclusão e o que a empresa deveria fazer.]

![Figura principal](saidas/figura_principal.png)

*[Legenda de 1 linha explicando o que a figura mostra e a base usada. Ex.: "Painel esquerdo: % de entregas acima de 35 min por cenário; direito: avaliação média por faixa de tempo. 8.058 pedidos, 2024."]*

---

## 1. Pergunta de negócio

[2–4 frases. Quem pediu a análise (a diretoria do app), para quê (planejar 2025) e quais as três frentes investigadas (operação, clientes, alavancas: cupons e chuva).]

**Perguntas que guiaram a análise:**
1. [Pergunta 1 — ex.: "Em que horários e dias da semana se concentram os pedidos?"]
2. [Pergunta 2]
3. [Pergunta 3]
4. [Pergunta 4]
5. [Pergunta 5]

## 2. Dados

- **Fonte:** `delivery_pedidos.csv`, fornecida no módulo DS-PY-018 (dados simulados de um app de delivery).
- **Período e escopo:** [ex.: 01/01/2024 a 31/12/2024; São Paulo, Rio de Janeiro e Belo Horizonte]
- **Tamanho:** [linhas × colunas da base original] → [linhas × colunas da base limpa]
- **Unidade de observação:** [ex.: um pedido]

### Dicionário da base limpa (`saidas/delivery_pedidos_limpo.csv`)

[Gere esta tabela pelo notebook (Tarefa 11.1) e complete a descrição. Inclua as colunas e as **flags** que vocês criaram.]

| Coluna | Tipo | Descrição | % faltantes | Observação / tratamento |
|---|---|---|---|---|
| `pedido_id` | int | identificador do pedido | 0 | — |
| `data_hora` | datetime | data e hora do pedido | 0 | convertida de texto |
| `cidade` | texto | cidade de entrega | 0 | [ex.: 13 variantes padronizadas para 3 nomes] |
| `valor_pedido` | float | valor dos itens em R$, sem taxa | 0 | [ex.: 720 valores no formato "R$ 44,02" convertidos] |
| `tempo_entrega_min` | float | minutos do pedido à entrega | [ ] | [ex.: 25 códigos 999 e 8 negativos → NaN] |
| `...` | | | | |
| `tempo_invalido` | bool | **flag** criada | 0 | [o que significa True] |
| `pedido_grande` | bool | **flag** criada | 0 | [critério usado] |

## 3. Como rodar

```bash
git clone [URL do repositório]
cd [pasta]
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
jupyter notebook projeto_final.ipynb
```

- O notebook lê o CSV original em `[caminho relativo, ex.: dados/delivery_pedidos.csv]`. [Explique onde colocar o arquivo, se ele não estiver no repositório.]
- Execute **Kernel → Restart & Run All**. Tempo aproximado: [ ] segundos.
- Versões usadas: Python [ ], pandas [ ], seaborn [ ], matplotlib [ ], scipy [ ] (ver `requirements.txt`).

## 4. Estrutura do repositório

```
.
├── README.md                     ← este arquivo
├── requirements.txt
├── projeto_final.ipynb           ← análise completa (Etapas 1 a 11)
├── autoavaliacao.md              ← ficha de autoavaliação preenchida
├── dados/
│   └── delivery_pedidos.csv      ← base original (NÃO editada)
└── saidas/
    ├── delivery_pedidos_limpo.csv
    └── figura_principal.png

```

## 5. Metodologia

[Resuma em 1 linha por etapa o que foi feito **e a decisão mais importante** de cada uma. Não copie o enunciado.]

1. **Perguntas e hipóteses** — [ ]
2. **Carga e inspeção** — [ex.: 3 colunas com tipo errado, 2 constantes, 3 com faltantes, valores impossíveis em 2]
3. **Limpeza** — [principais transformações e quantas linhas cada uma afetou]
4. **Outliers** — [o que foi considerado erro e o que foi mantido como legítimo, e por quê]
5. **Estatística descritiva** — [ ]
6. **Sumarização e granularidade** — [quais granularidades e o que cada uma revelou]
7. **Visualização** — [padrão visual adotado]
8. **Correlação** — [ ]
9. **Testes de hipótese** — [testes usados e nível de significância]
10. **Conclusões** — [ ]

### Decisões de limpeza

| Problema | Linhas afetadas | Decisão | Alternativa considerada |
|---|---|---|---|
| [ex.: `tempo_entrega_min` = 999] | [25] | [→ NaN + flag] | [remover a linha] |
| [ ] | | | |

## 6. Principais achados

[5 achados. Cada um: **frase com número** + de onde veio + por que importa. Os números precisam bater com o notebook.]

1. **[Achado 1 em negrito].** [Número + evidência (teste/tarefa) + consequência.]
2. **[Achado 2].** [ ]
3. **[Achado 3].** [ ]
4. **[Achado 4].** [ ]
5. **[Achado 5].** [ ]

### Hipóteses testadas (α = 5%)

[Cole a tabela da Tarefa 9.7.]

| Hipótese | Teste | p-valor | Efeito | Decisão | Em linguagem de negócio |
|---|---|---|---|---|---|
| H1 chuva × tempo de entrega | [ ] | [ ] | [ex.: +9 min] | [ ] | [ ] |
| H2 cupom × ticket | | | | | |
| H3 tempo × avaliação | | | | | |
| H4 cozinha × ticket | | | | | |
| H5 cidade × forma de pagamento | | | | | |
| H6 [hipótese criada] | | | | | |

## 7. Recomendações

| # | Recomendação | Achados que sustentam | Métrica para acompanhar |
|---|---|---|---|
| 1 | [ ] | [ ] | [ ] |
| 2 | [ ] | [ ] | [ ] |
| 3 | [ ] | [ ] | [ ] |

## 8. Limitações

[Pelo menos 3. O que os dados **não** permitem afirmar e por quê. Ex.: ausência de `cliente_id`, ausência de custo do cupom, dados observacionais, um único ano.]

- [ ]
- [ ]
- [ ]

## 9. Próximos passos

[O que vocês fariam com mais tempo ou mais dados — de preferência transformando cada limitação em uma ação.]

- [ ]
- [ ]

## 10. Autores

| Nome | GitHub | Principais contribuições |
|---|---|---|
| [ ] | [@usuario] | [ex.: limpeza e outliers (Etapas 3–4), README] |
| [ ] | [@usuario] | [ ] |
| [ ] | [@usuario] | [ ] |

*Projeto final do módulo DS-PY-018 · Análise Exploratória de Dados · [turma, mês/ano]*

---

<!--
CHECKLIST ANTES DE PUBLICAR (apague este bloco no README final)
[ ] Todos os [colchetes] foram substituídos
[ ] A figura principal aparece no topo (caminho relativo correto)
[ ] Os números do README batem com o notebook executado
[ ] "Como rodar" foi testado num clone limpo do repositório
[ ] requirements.txt existe e tem versões
[ ] Histórico de commits com mensagens descritivas
-->
