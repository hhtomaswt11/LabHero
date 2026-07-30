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
**Tema:** comparação controlada de funções objetivo em FBA.  
**Explica:** alterar a função objetivo muda a pergunta matemática feita ao mesmo espaço de soluções; não altera biologicamente a estirpe nem o meio. Maximizar diretamente etanol pode encontrar um máximo teórico com biomassa igual a zero.  
**Como passar:** depois da Missão 06, registar dois runs visíveis com FBA, genes todos ativos, ambiente default e `EX_etoh_e` acompanhado. No primeiro, usar `BIOMASS_Ecoli_core_w_GAM` como objetivo; no segundo, usar `EX_etoh_e`. O relatório deve confirmar aproximadamente biomassa `0.874`, etanol `0` e captação de O2 `21.799` no primeiro run, e biomassa `0`, etanol `20` e captação de O2 `0` no segundo.

### Mission 08 — Constraint Impact on the Optimal Solution
**Tema:** comparação controlada do impacto de uma restrição ambiental no ótimo.  
**Explica:** adicionar uma restrição só altera o ótimo quando exclui ou limita soluções necessárias para atingir o ótimo anterior. No ótimo direto de D-lactato, o meio default já apresenta captação de O2 igual a zero; fechar O2 reduz o espaço admissível, mas não altera D-lactato, biomassa ou oxigénio. No run restringido, o bound de oxigénio é atingido em igualdade, sem alterar o ótimo relativamente ao run default.  
**Como passar:** depois da Missão 07, registar dois runs visíveis com FBA, objetivo `EX_lac__D_e`, todos os genes ativos e `EX_lac__D_e` acompanhado. No primeiro usar o meio completamente default; no segundo fechar apenas o lower bound de `EX_o2_e`. Ambos devem apresentar aproximadamente D-lactato `20`, biomassa `0` e captação de O2 `0`, permitindo concluir que o fecho do oxigénio não aumentou o produto.

### Mission 09 — Integrated Environment-and-Gene Design
**Tema:** integração de meio, objetivo de biomassa, produção acompanhada e um knockout.  
**Explica:** uma estratégia de engenharia metabólica deve ser comparada com um baseline no mesmo meio e avaliada pela produção e pela retenção de crescimento na mesma solução visível.  
**Como passar:** depois da Missão 08, fechar a captação de glicose, abrir L-malato como fonte substituta, manter oxigénio e restantes bounds inalterados, usar FBA com biomassa, acompanhar `EX_for_e`, registar um baseline sem knockout e testar individualmente `b1479`, `b0721`, `b0116` e `b0115`. A evidência identifica `b0115 / aceF` como o único design que retém pelo menos 80% do crescimento e aumenta formate em pelo menos 1.0.

### Mission 10 — Two-Gene Redundancy and Flux Redirection
**Tema:** redundância genética em regras GPR `OR`, pares de knockouts e redirecionamento de fluxos.  
**Explica:** um knockout isolado pode deixar uma reação funcional através de um gene alternativo. Um par adequado pode desativar a rota, aumentar etanol e reduzir acetato, mas deve manter crescimento suficiente. Todos os valores são lidos da mesma solução FBA que maximiza biomassa.  
**Como passar:** depois da Missão 09, manter a glicose default, fechar apenas o lower bound de `EX_o2_e`, usar FBA com objetivo `BIOMASS_Ecoli_core_w_GAM`, acompanhar `EX_etoh_e` e `EX_ac_e`, registar um baseline sem knockouts e testar os seis pares formados por `b2297`, `b2458`, `b1241` e `b0351`. A evidência identifica `b2297 + b2458` (`pta + eutD`) como o único par que retém pelo menos 80% do crescimento e aumenta etanol em pelo menos 5.0.

## Lab 5 — Dr. Almeida

### Mission 11 — Anaerobic Secretion Fingerprint
**Tema:** diagnóstico de uma solução através da biomassa e de um painel completo de fluxos de troca.  
**Explica:** o valor da função objetivo não descreve sozinho o fenótipo previsto. Um fluxo de troca positivo indica secreção nesta solução; um fluxo zero descreve apenas este modelo, objetivo e conjunto de restrições, não uma incapacidade biológica universal.  
**Como passar:** depois da Missão 10, usar FBA com objetivo `BIOMASS_Ecoli_core_w_GAM`, todos os genes ativos, glicose default, apenas o lower bound de `EX_o2_e` fechado e restantes bounds inalterados. Acompanhar numericamente `EX_for_e`, `EX_ac_e`, `EX_etoh_e`, `EX_lac__D_e` e `EX_succ_e` na mesma solução visível. O fingerprint deve apresentar aproximadamente crescimento `0.212`, formate `17.805`, acetato `8.504`, etanol `8.279`, D-lactato `0` e succinato `0`. Entregar `formate` / `EX_for_e` como produto dominante.

### Mission 12 — Constraint-Driven Succinate Byproducts
**Tema:** comparação controlada de dois fingerprints produto-ótimos e identificação de uma restrição vinculativa.  
**Explica:** o efeito de uma restrição depende do objetivo e do fluxo utilizado pelo ótimo anterior. Com `EX_succ_e` como objetivo, retirar oxigénio reduz o máximo teórico de succinato e introduz acetato como coproduto previsto. Ambos os ótimos têm biomassa aproximadamente zero e não representam estirpes produtivas viáveis.  
**Como passar:** depois da Missão 11, usar FBA com objetivo `EX_succ_e`, todos os genes ativos, glicose default e o painel completo `EX_succ_e`, `EX_ac_e`, `EX_for_e`, `EX_etoh_e`, `EX_lac__D_e`. Registar um run com ambiente completamente default e outro em que apenas o lower bound de `EX_o2_e` está fechado, por qualquer ordem. A comparação deve mostrar succinato aproximadamente `16.384 → 13.906`, oxigénio `2.655 → 0`, acetato `0 → 5.665` e biomassa `0` nos dois runs. Entregar `acetate` / `EX_ac_e` como novo coproduto positivo.

### Mission 13 — Primary Objective and Flux Parsimony
**Tema:** comparação controlada entre FBA e pFBA, distinguindo objetivo primário e critério secundário.  
**Explica:** pFBA preserva o ótimo primário de `EX_succ_e` e minimiza a soma dos valores absolutos dos fluxos como segundo critério. O score pFBA não representa succinato adicional. O fingerprint externo pode permanecer igual, e a igualdade de fluxo total é válida quando o solver FBA já devolveu uma solução parcimoniosa.  
**Como passar:** depois da Missão 12, usar `EX_succ_e`, todos os genes ativos, glicose default, apenas o lower bound de `EX_o2_e` fechado e o painel completo `EX_succ_e`, `EX_ac_e`, `EX_for_e`, `EX_etoh_e`, `EX_lac__D_e`. Registar um run FBA e um run pFBA por qualquer ordem. Ambos devem apresentar aproximadamente succinato `13.906`, acetato `5.665`, restantes produtos `0`, biomassa `0`, glicose `10` e oxigénio `0`. O pFBA não pode usar mais fluxo total do que o FBA para além da tolerância. Entregar `total flux`, `total absolute flux` ou equivalente.

### Mission 14 — Byproduct Trade-off Screening
**Tema:** screening controlado de intervenções genéticas e avaliação do perfil completo de trade-offs.  
**Explica:** reduzir um único coproduto não prova que a intervenção melhorou. É necessário verificar retenção do alvo, redução de acetato e aparecimento de novos produtos. Um resultado negativo também é cientificamente válido.  
**Como passar:** depois da Missão 13, usar `pFBA`, objetivo `EX_succ_e`, glicose default, apenas o lower bound de `EX_o2_e` fechado e o painel completo `EX_succ_e`, `EX_ac_e`, `EX_for_e`, `EX_etoh_e`, `EX_lac__D_e`. O run pFBA visível da Missão 13 pode ser reutilizado como referência. Testar individualmente `b1241 / adhE`, `b0115 / aceF`, `b0474 / adk` e `b4151 / frdD`. Uma melhoria limpa teria de reter pelo menos 90% do succinato, reduzir acetato em pelo menos 1.0 e não criar novo coproduto acima de 0.1. Nenhum candidato cumpre tudo; entregar `none`, `no candidate`, `nenhum` ou equivalente.

### Mission 15 — Product–Growth Viability Audit
**Tema:** comparação controlada entre um ótimo de produto e um ótimo de crescimento.  
**Explica:** um máximo teórico de produto não demonstra automaticamente uma solução compatível com crescimento. A função objetivo muda a solução selecionada, pelo que biomassa e produto devem ser inspecionados cruzadamente sob a mesma estirpe e meio.  
**Como passar:** depois da Missão 14, usar `pFBA`, todos os genes ativos, glicose default, apenas o lower bound de `EX_o2_e` fechado e o painel completo `EX_succ_e`, `EX_ac_e`, `EX_for_e`, `EX_etoh_e`, `EX_lac__D_e`. Registar um run com objetivo `EX_succ_e` e outro com `BIOMASS_Ecoli_core_w_GAM`, mantendo tudo o resto idêntico. O primeiro deve mostrar succinato aproximadamente `13.906` e biomassa `0`; o segundo, biomassa aproximadamente `0.212` e succinato `0`. Entregar uma conclusão escrita coerente com os dois valores cruzados.
