# LabHero — Mission Progress Overview

Resumo curto das missões implementadas até agora, organizado por laboratório.

## Lab 1 — Dr. Martinez

### Mission 01 — Anaerobic Growth
**Tema:** ambiente e respiração.  
**Explica:** como uma restrição ambiental altera o crescimento previsto por FBA.  
**Como passar:** correr FBA com objective de biomassa e fechar o lower bound do O2 (`EX_o2_e`).

### Mission 02 — Alternative Carbon Source
**Tema:** nutrientes/substratos.  
**Explica:** que diferentes fontes de carbono podem suportar crescimento de forma diferente.  
**Como passar:** substituir glucose por fructose e entregar `fructose`.

## Lab 2 — Dr. Silva

### Mission 03 — Essential Gene Knockout
**Tema:** genes essenciais.  
**Explica:** um knockout pode inviabilizar crescimento se o gene for essencial.  
**Como passar:** testar genes candidatos e entregar `b2926` / `pgk`.

### Mission 04 — Production Knockout
**Tema:** knockout para redirecionar produção.  
**Explica:** remover um gene pode aumentar produção de um produto sem mexer no ambiente.  
**Como passar:** manter ambiente default, objective de biomassa, desligar `b2297` / `pta`.

### Mission 05 — Anaerobic Production Knockout
**Tema:** knockout + ambiente anaeróbio.  
**Explica:** produção fermentativa pode depender de ambiente e knockout.  
**Como passar:** fechar lower bound do O2 e desligar `b1241` / `adhE`.

## Lab 3 — Dr. Carter

### Mission 06 — Growth vs Production
**Tema:** equilíbrio crescimento/produção.  
**Explica:** mais alterações nem sempre dão melhor resultado; o score combina crescimento e produção.  
**Como passar:** manter ambiente default, objective de biomassa, desligar `b2297` / `pta`.

## Lab 4 — Dr. Nova

### Mission 07 — Objective Matters
**Tema:** função objetivo.  
**Explica:** mudar a objective muda o alvo da simulação.  
**Como passar:** objective `EX_etoh_e`, sem knockouts e sem alterações ambientais.

### Mission 08 — Objective Under Constraints
**Tema:** objective + restrição ambiental.  
**Explica:** uma objective de produção pode precisar de um contexto ambiental coerente.  
**Como passar:** objective `EX_lac__D_e`, fechar lower bound do O2, sem knockouts.

### Mission 09 — Integrated Strain Design
**Tema:** objective + ambiente + 1 knockout.  
**Explica:** desenho de estirpes combina várias decisões de modelação.  
**Como passar:** objective `EX_lac__D_e`, fechar lower bound do O2, desligar `b1241` / `adhE`.

### Mission 10 — Multi-Knockout Robust Design
**Tema:** design robusto com evidência de fluxos.  
**Explica:** um design mais robusto precisa de vários knockouts e fluxos acompanhados.  
**Como passar:** objective `EX_lac__D_e`, fechar lower bound do O2, desligar `b1241` + `b2297`, acompanhar `EX_lac__D_e` + `EX_etoh_e`.

## Lab 4 — Dr. Almeida

### Mission 11 — Flux Fingerprint
**Tema:** diagnóstico por Production Flux.  
**Explica:** o valor da objective não chega; é preciso ver o que a célula secreta.  
**Como passar:** FBA, objective de biomassa, fechar lower bound do O2, sem knockouts, acompanhar `EX_ac_e`, `EX_for_e`, `EX_etoh_e`, `EX_lac__D_e`, `EX_succ_e`.

### Mission 12 — Competing Byproducts
**Tema:** produto alvo vs subprodutos.  
**Explica:** produzir um alvo também implica analisar produtos concorrentes.  
**Como passar:** FBA, objective `EX_succ_e`, fechar lower bound do O2, sem knockouts, acompanhar `EX_succ_e` e pelo menos dois subprodutos candidatos.

### Mission 13 — FBA vs pFBA
**Tema:** método de simulação.  
**Explica:** pFBA procura uma distribuição de fluxos mais parcimoniosa para a mesma objective.  
**Como passar:** pFBA, objective `EX_succ_e`, fechar lower bound do O2, sem knockouts, acompanhar `EX_succ_e` + subprodutos.

### Mission 14 — Byproduct Reduction Design
**Tema:** reduzir subproduto indesejado.  
**Explica:** otimizar uma estirpe não é só aumentar produto alvo; também pode ser reduzir subprodutos.  
**Como passar:** pFBA, objective `EX_succ_e`, fechar lower bound do O2, desligar `b1241` / `adhE`, acompanhar `EX_succ_e` + `EX_etoh_e`.

### Mission 15 — Final Diagnostic Report
**Tema:** relatório diagnóstico completo.  
**Explica:** uma solução deve ser justificada por método, objective, ambiente, knockout e painel completo de fluxos.  
**Como passar:** pFBA, objective `EX_succ_e`, fechar lower bound do O2, desligar `b1241` / `adhE`, acompanhar `EX_succ_e`, `EX_etoh_e`, `EX_ac_e`, `EX_for_e`, `EX_lac__D_e`.
