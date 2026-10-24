# TigrIFES

Laboratório de probabilidade com uma máquina de rolos didática e os cinco experimentos do Trabalho I de Probabilidade e Estatística I, IFES – Campus Serra.

**Simulador acadêmico - somente créditos fictícios.** A publicação principal é um site estático compatível com GitHub Pages e domínio próprio. Os giros funcionam no navegador; o modelo e os experimentos também estão implementados em Python para estudo e conferência.

## Executar a versão estática

O ambiente virtual `.venv` já está preparado neste checkout. Na raiz do projeto:

```powershell
.\.venv\Scripts\python.exe -m tigrifes.build_site --output site
.\.venv\Scripts\python.exe -m http.server 8000 --directory site --bind 127.0.0.1
```

Abra **http://127.0.0.1:8000**. Encerre com `Ctrl+C`. Esse servidor apenas entrega os arquivos estáticos; os giros são calculados no navegador.

Também há um iniciador que cria o ambiente quando necessário, gera o site e inicia a prévia:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

O parâmetro `-ExecutionPolicy Bypass` só vale para esse processo. Os comandos diretos de Python dispensam o script PowerShell.

Em outro computador, instale Python 3.13 e prepare as dependências de construção:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c constraints.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m tigrifes.build_site
```

No Linux/macOS, use `python3.13 -m venv .venv` e `.venv/bin/python` no lugar de `.\.venv\Scripts\python.exe`. O visitante do site não precisa instalar Python, Node.js ou bibliotecas.

## Funcionamento e persistência

- Tabuleiro 3 × 3 com rolos circulares A, B, C, D e E; prêmio apenas na linha central.
- Custo fixo de 1 crédito, prêmio bruto e lucro líquido apresentados separadamente.
- Sessão com 100 créditos, até 500 rodadas ou esgotamento; reinício com escolha de semente.
- Histórico das últimas 12 rodadas e trajetória do saldo da sessão inteira.
- Sessão salva somente no navegador. Recarregar restaura os resultados; limpar os dados do site apaga a sessão. Se o armazenamento estiver bloqueado, a página funciona em memória e informa essa condição.
- Sincronização entre abas da mesma instalação. Web Locks serializa alterações quando disponível; revisão da sessão e eventos de armazenamento detectam mudanças no fallback.
- Instalações em caminhos distintos usam chaves separadas. Navegadores, dispositivos e domínios diferentes não compartilham sessões.
- Interface em português, layout responsivo, botões nativos, foco visível, mensagens com `aria-live`, símbolos identificados por letras e suporte a movimento reduzido.

O navegador persiste apenas semente, número de rodadas e revisão. Ao restaurar, os resultados são recompostos pela semente. Não há proteção contra manipulação pelo próprio visitante: os créditos são fictícios.

Scripts, estilos, gráficos e dados são locais. Não há chamadas a API ou CDN durante o jogo. Experimentos e downloads funcionam com JavaScript desativado.

## Regras e contas

Uma parada uniforme `K` entre 0 e 4 gera a coluna `R[K]`, `R[(K+1) % 5]`, `R[(K+2) % 5]`. Os três rolos e as novas rodadas são independentes. As células da mesma coluna são dependentes, pois são posições vizinhas.

| Centro | Prêmio P | Lucro X = P − 1 | Probabilidade |
|---|---:|---:|---:|
| AAA | 5 | 4 | 1/125 |
| BBB | 10 | 9 | 1/125 |
| CCC | 15 | 14 | 1/125 |
| DDD | 25 | 24 | 1/125 |
| EEE | 50 | 49 | 1/125 |
| Qualquer outra tripla | 0 | −1 | 120/125 |

Há `5³ = 125` triplas centrais equiprováveis. A chance de prêmio é `5/125 = 4%`. O prêmio médio é `(5+10+15+25+50)/125 = 0,84`, o lucro esperado é `−0,16` crédito por rodada e o RTP é 84%. RTP não é chance de prêmio nem garantia de retorno individual.

Para um número **fixo** de rodadas `n`, o lucro total esperado é `−0,16n`. Não aplique automaticamente essa conta às sessões com duração dependente do saldo.

## Mesmo sorteio em Python e JavaScript

O Python usa `random.Random` / Mersenne Twister com três chamadas a `randrange(5)` por rodada. A semente é inicializada uma vez por execução.

O JavaScript implementa MT19937 com inicialização inteira compatível com CPython 3.13 para sementes entre `0` e `4.294.967.295`. A escolha de paradas reproduz `getrandbits(3)` com rejeição de 5, 6 e 7; não usa resto por 5 nem `Math.random` para sortear símbolos. A compatibilidade é específica desse intervalo e de `randrange(5)`, não de toda a API `random`.

Os testes comparam exatamente **80.000 rodadas**: 10.000 para cada semente `0, 1, 10, 42, 2026, 123456, 2147483648, 4294967295`. As três paradas de cada rodada precisam coincidir. Referências: [núcleo do gerador CPython](https://github.com/python/cpython/blob/3.13/Modules/_randommodule.c), [seleção discreta em random.py](https://github.com/python/cpython/blob/3.13/Lib/random.py) e [atribuição/licença MT19937](LICENSES/MT19937.txt).

## Cinco experimentos

O site publica resultados calculados em Python durante sua construção. Giros de visitantes não modificam esses dados. Para exportar somente os experimentos:

```powershell
.\.venv\Scripts\python.exe -m tigrifes.experiments --output results
```

| Experimento | Procedimento |
|---|---|
| E1 — Frequências | 10.000 rodadas, semente 2026, sem saldo. Seis categorias, lucro médio, RTP, frequência de prêmio e desvio-padrão amostral (N − 1). |
| E2 — Convergência | Sementes 10, 2026 e 123456; reutiliza o E1. Médias após 100, 1.000 e 10.000 rodadas, trajetórias e reprodução dos dez primeiros resultados. |
| E3 — Saldo limitado | 100 participantes, saldo 100, até 500 rodadas. Semente 42 contínua entre participantes; média, mediana, categorias e trajetórias dos cinco primeiros. |
| E4 — Independência | 9.999 pares consecutivos do E1; proporções de prêmio após prêmio e após ausência de prêmio. Grupo vazio resulta em proporção não estimável. |
| E5 — Pagamentos | Tabelas base e +10% sobre os mesmos resultados do E1. Valores fracionários pertencem somente à comparação. |

O ZIP inclui CSV dos 30.000 sorteios, tabelas dos cinco experimentos, 100 participantes, cinco trajetórias, gráficos PNG/SVG, `resumos.json` e `metadata.json`. Os metadados registram sementes, parâmetros, gerador e versões. Nos dados brutos, probabilidades, frequências e RTP são proporções: `0.84 = 84%`. CSV: UTF-8 com BOM, separador vírgula e ponto decimal; no Excel em português, importe por **Dados → De Texto/CSV**.

As dependências principais são Jinja2, para os templates, e matplotlib, para os gráficos. A construção usa `constraints.txt` e a série Python 3.13. Confira também a versão exata do Python nos metadados ao reproduzir uma entrega.

Referência validada em CPython 3.13.13:

- E1: lucro médio **−0,1315** crédito; RTP **86,85%**; prêmio em **4,12%** das rodadas; desvio-padrão **5,2750** créditos.
- E3: **23** com ganho, **2** empatados, **75** com perda; **67** esgotaram o saldo. Média final **52,10** e mediana **0** créditos.
- E4: **9.587** pares após ausência de prêmio e **412** após prêmio, total **9.999**.

Os valores observados não substituem a teoria. Os dados descrevem um modelo didático, não famílias reais, transtornos ou impactos nacionais. A discussão social exige fontes documentais externas.

## Testes e validação

Instale Node.js 22+ para a comparação entre linguagens e os testes JavaScript. Não há pacotes npm a instalar.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node --test tests/js/*.test.cjs
```

As verificações cobrem 125 combinações, pagamentos, lucro, sementes, totais dos experimentos, exportações, compatibilidade entre linguagens, links relativos e âncoras, página 404 em URLs aninhadas, importação do modelo apenas com a biblioteca padrão, restauração, paradas, armazenamento bloqueado/corrompido, revisões antigas e interação dos botões em DOM mínimo.

Não havia navegador conectado para inspeção visual real. Os testes de DOM não substituem a conferência de layout e navegação por teclado em um navegador.

## Estrutura

```text
tigrifes/machine.py               modelo Python
tigrifes/experiments.py           cinco experimentos e exportações
tigrifes/build_site.py            construção das páginas estáticas
tigrifes/templates/              templates das páginas estáticas
tigrifes/static/machine.js       motor JavaScript compatível com Python
tigrifes/static/session-store.js persistência local e revisões
tigrifes/static/app-static.js    interação do site estático
site/                           saída gerada, fora do Git
.github/workflows/pages.yml      testes e publicação no Pages
tests/                          testes Python e JavaScript
docs/DEPLOYMENT.md               publicação e DNS get.tech
LICENSES/                       atribuição do gerador
```