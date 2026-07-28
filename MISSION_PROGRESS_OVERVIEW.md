# LabHero — Mission Progress Overview

Resumo curto das missões implementadas até agora, organizado por laboratório.

## Lab 1 — Dr. Martinez

### Mission 01 — Anaerobic Growth
**Tema:** ambiente e respiração.  
**Explica:** como a remoção de oxigénio altera o crescimento previsto por FBA sem impedir necessariamente a viabilidade.  
**Como passar:** realizar uma comparação controlada: primeiro FBA com objetivo de biomassa e meio original; depois repetir alterando apenas o lower bound de `EX_o2_e` para zero. O segundo run deve manter crescimento positivo, apresentar crescimento inferior ao baseline e captação de oxigénio igual a zero.

### Mission 02 — Alternative Carbon Source
**Tema:** nutrientes/substratos e desenho de experiências controladas.  
**Explica:** que diferentes fontes de carbono podem suportar crescimento de forma diferente e que uma comparação válida exige remover a glucose, testar uma única alternativa de cada vez e manter as restantes condições equivalentes.  
**Como passar:** realizar os dez ensaios candidatos com FBA, objetivo de biomassa, genes ativos, glucose indisponível e o mesmo limite molar de captação (`-10`) para cada fonte; depois entregar a fonte que apresenta o maior crescimento previsto.

## Lab 2 — Dr. Silva

### Mission 03 — Essential Gene Knockout
**Tema:** genes essenciais.  
**Explica:** um knockout pode inviabilizar crescimento se o gene for essencial.  
**Como passar:** testar genes candidatos e entregar `b2926` / `pgk`.

### Mission 04 — Growth-Coupled Ethanol Production
**Tema:** knockout para redirecionar fluxo para produção mantendo crescimento previsto.  
**Explica:** uma redução de crescimento não prova, por si só, uma estratégia de produção; é necessário acompanhar diretamente o produto e manter a comparação controlada.  
**Como passar:** registar um baseline sem knockouts e testar individualmente `b1241`, `b0728`, `b3736` e `b2278`, sempre com FBA, objetivo de biomassa, ambiente aeróbio default e `EX_etoh_e` acompanhado. Entregar `b2278` / `nuoL`, o único candidato que aumenta significativamente o etanol e mantém crescimento acima do critério operacional de viabilidade.

### Mission 05 — Context-Dependent Anaerobic Ethanol Design
**Tema:** interação entre ambiente, genética, crescimento e produção.  
**Explica:** uma estratégia genética útil em aerobiose pode tornar-se neutra em anaerobiose; o melhor knockout depende das restrições ambientais e da função objetivo.  
**Como passar:** registar um baseline anaeróbio sem knockouts e testar individualmente `b2278`, `b0728`, `b1602` e `b3736`, sempre com FBA, objetivo de biomassa, apenas o lower bound de `EX_o2_e` fechado e `EX_etoh_e` acompanhado. Entregar `b3736` / `atpF`, o candidato elegível com maior secreção adicional de etanol mantendo pelo menos 90% do crescimento anaeróbio de referência.

## Lab 3 — Dr. Carter

### Mission 06 — Controlled Multi-Knockout Challenge
**Tema:** equilíbrio crescimento/produção com orçamento genético limitado.  
**Explica:** mais alterações nem sempre melhoram uma estirpe; o índice competitivo só é comparável quando meio, modelo, objetivo e orçamento permanecem fixos.  
**Como passar:** registar uma referência aeróbia default sem knockouts; usar FBA com objetivo de biomassa, acompanhar `EX_etoh_e`, manter o meio completamente inalterado e testar apenas `b2278`, `b3736`, `b1602` e `b0728`, com no máximo dois knockouts. O melhor design é `b2278 + b3736`, com índice aproximadamente `2.876`, acima do rival `2.800`, mantendo mais de 20% do crescimento de referência.

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
