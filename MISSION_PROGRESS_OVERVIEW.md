# LabHero — Mission Progress Overview

Resumo das 40 missões implementadas na versão atual do LabHero, organizado por laboratório.

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

## Lab 6 — Dr. Rio

### Mission 16 — Context-Dependent Carbon Rescue
**Tema:** screening controlado de fontes de carbono e robustez perante uma segunda alteração ambiental.  
**Explica:** uma fonte que apresenta o maior crescimento sob um protocolo molar comum pode depender de outro componente do meio. A classificação é específica do modelo e dos bounds usados; um resultado `INFEASIBLE` após retirar oxigénio não constitui uma impossibilidade experimental universal.  
**Como passar:** depois da Missão 15, usar FBA com objetivo de biomassa, todos os genes ativos, fechar a captação de glicose e testar individualmente `EX_ac_e`, `EX_pyr_e`, `EX_mal__L_e`, `EX_fum_e` e `EX_akg_e`, mantendo oxigénio e todos os restantes bounds no default. O Exchange Flux Report deve confirmar glucose `0`, fonte alternativa aproximadamente `10` e oxigénio positivo em cada run. Depois dos cinco ensaios, repetir a fonte com maior crescimento (`EX_akg_e`) fechando apenas a captação de oxigénio. O resultado visível deve ser `INFEASIBLE`. Entregar `oxygen`, `O2`, `EX_o2_e` ou equivalente curto.


### Mission 17 — Essential Uptake Routes
**Tema:** baseline controlado, screening de cinco lower bounds e interpretação da direção de fluxos de troca.  
**Explica:** um lower bound de exchange controla capacidade de uptake, mas o mesmo exchange pode continuar a permitir secreção positiva. A conclusão deve ser feita relativamente ao crescimento baseline e é específica deste modelo, objetivo e meio.  
**Como passar:** depois da Missão 16, registar um baseline FBA com objetivo `BIOMASS_Ecoli_core_w_GAM`, genes ativos e ambiente totalmente default. Depois fechar separadamente o lower bound de `EX_nh4_e`, `EX_pi_e`, `EX_h2o_e`, `EX_h_e` e `EX_co2_e`, mantendo todos os restantes bounds default e usando o Exchange Flux Report completo. O screening deve apresentar dois crescimentos próximos de zero e três valores próximos do baseline `0.874`. Entregar as duas rotas suportadas pelos dados; a ordem é indiferente.

### Mission 18 — Binding Export Constraints
**Tema:** comparação causal entre uma upper-bound constraint binding e um controlo não-binding.  
**Explica:** fechar um upper bound restringe exportação positiva, mas a constraint só altera o ótimo quando a solução baseline usa essa direção de fluxo. Uma constraint pode estar presente sem ser binding.  
**Como passar:** depois da Missão 17, registar um baseline FBA com objetivo `BIOMASS_Ecoli_core_w_GAM`, todos os genes ativos, glicose default, apenas o lower bound de `EX_o2_e` fechado e o painel completo `EX_ac_e`, `EX_etoh_e`, `EX_for_e`, `EX_succ_e`, `EX_lac__D_e`. Depois repetir o mesmo protocolo fechando separadamente o upper bound de `EX_ac_e` e de `EX_succ_e`. O primeiro trial deve manter crescimento viável mas alterar o perfil; o segundo deve preservar o baseline. Entregar a rota cuja closure foi binding.

### Mission 19 — Re-optimisation vs Minimal Adjustment
**Tema:** comparação controlada entre re-optimização FBA e ajustamento mínimo lMOMA após o mesmo knockout.  
**Explica:** FBA maximiza novamente a biomassa admissível, enquanto Linear MOMA (`lMOMA`) minimiza a soma dos desvios absolutos relativamente a uma referência FBA wild type explícita, calculada no mesmo meio antes do knockout. O score lMOMA não é biomassa; a biomassa é lida da reação `BIOMASS_Ecoli_core_w_GAM` na mesma solução visível.  
**Como passar:** depois da Missão 18, registar um baseline wild type com FBA, objetivo de biomassa, genes ativos, meio completamente default e o painel `EX_ac_e`, `EX_etoh_e`, `EX_for_e`, `EX_lac__D_e`, `EX_succ_e`. Depois desligar apenas `b0728 / sucC`, que desativa `SUCOAS` pela regra GPR completa, e registar o mutante primeiro com FBA e depois com lMOMA, mantendo tudo o resto idêntico. A comparação deve apresentar aproximadamente biomassa `0.874` no WT, `0.858` no mutante FBA e `0.803` no mutante lMOMA, além de um score de ajustamento lMOMA próximo de `39.785`. Entregar o método que produziu a menor resposta de biomassa ainda viável.

### Mission 20 — Context-Specific Export Robustness
**Tema:** matriz controlada de robustez entre contexto de oxigénio e uma upper-bound constraint de exportação.  
**Explica:** a mesma closure do upper bound de acetato pode ser não-binding quando o ótimo baseline não exporta acetato e provocar uma redistribuição mensurável quando o contexto ambiental utiliza essa rota. A presença de uma constraint não demonstra, por si só, que ela limita a solução.  
**Como passar:** depois da Missão 19, usar `pFBA`, objetivo `BIOMASS_Ecoli_core_w_GAM`, todos os genes ativos, glucose default e o painel `EX_ac_e`, `EX_etoh_e`, `EX_for_e`, `EX_succ_e`, `EX_lac__D_e`. Registar os quatro pares formados por oxigénio disponível/fechado e upper bound de `EX_ac_e` aberto/fechado, mantendo todos os restantes bounds default. No contexto com oxigénio, a closure deve preservar crescimento, perfil e diagnósticos aproximadamente iguais; no contexto com captação de oxigénio fechada, deve eliminar acetato, manter crescimento viável e redistribuir o perfil, sobretudo para etanol. Entregar o contexto de oxigénio suportado pela comparação.

## Lab 7 — Dr. Vega

### Mission 21 — Compensatory Flux Comparison
**Tema:** comparação quantitativa antes/depois e identificação de um fluxo compensatório.  
**Explica:** o maior valor final e o maior aumento não são a mesma medida. Ao fechar uma rota de exportação ativa, uma solução ainda viável pode redistribuir fluxo para outra secreção; a atribuição causal requer que apenas um bound mude entre os dois runs.  
**Como passar:** depois da Missão 20, usar FBA com objetivo `BIOMASS_Ecoli_core_w_GAM`, todos os genes ativos, glucose default, apenas o lower bound de `EX_o2_e` fechado e o painel `EX_ac_e`, `EX_etoh_e`, `EX_for_e`, `EX_succ_e`, `EX_lac__D_e`. Registar uma referência com o upper bound de `EX_etoh_e` aberto e outro run fechando apenas esse upper bound. O segundo run deve permanecer viável e o relatório deve calcular as diferenças `modificado - referência`. Entregar a única rota com o maior aumento positivo.

### Mission 22 — Phenotype Equivalence Audit
**Tema:** equivalência observacional entre uma intervenção ambiental e uma intervenção genética com mecanismo diferente.  
**Explica:** dois mecanismos distintos podem produzir os mesmos outputs registados sob um painel fenotípico limitado. Igualdade de crescimento, captações e secreções não prova igualdade mecanística; apenas mostra que o painel observado não distingue as intervenções dentro da tolerância.  
**Como passar:** depois da Missão 21, usar FBA com objetivo `BIOMASS_Ecoli_core_w_GAM`, glucose default, apenas o lower bound de `EX_o2_e` fechado e o painel `EX_ac_e`, `EX_etoh_e`, `EX_for_e`, `EX_succ_e`, `EX_lac__D_e`. Registar uma intervenção ambiental com todos os genes ativos e o upper bound de `EX_ac_e` fechado. Registar também uma intervenção genética com o upper bound de acetato default e apenas `b2297 / pta` + `b2458 / eutD` desligados, confirmando `PTAr` como reação desativada pela GPR completa. Os dois fenótipos devem apresentar aproximadamente crescimento `0.189`, glucose `10`, oxigénio `0`, acetato `0`, etanol `16.584`, formate `3.956`, succinato `0` e D-lactato `0`. Entregar o número de outputs registados cuja diferença excede a tolerância.


## Lab 8 — Dr. Luna

### Mission 23 — Nutrient Sensitivity Curve
**Tema:** curvas de resposta, limitação gradual de nutrientes e início de uma secreção de overflow.  
**Explica:** um lower bound define capacidade de uptake, não necessariamente o fluxo utilizado. Um sweep permite distinguir um ponto não-binding do primeiro ponto limitante e observar uma resposta metabólica não linear.  
**Como passar:** depois da Missão 22, usar `pFBA`, objetivo `BIOMASS_Ecoli_core_w_GAM`, todos os genes ativos e ambiente base completamente default. No `Bound Sweep Setup`, selecionar o lower bound de `EX_nh4_e` e os valores `-5`, `-4`, `-2`, `-1`. Em `Production Flux`, selecionar apenas o painel contextual `EX_ac_e` e `EX_co2_e`. O relatório deve registar numericamente biomassa, uptake de amónio, glucose, oxigénio e fosfato, os dois fluxos acompanhados e os diagnósticos pFBA em cada linha. O ponto `-5` mantém crescimento aproximadamente `0.874` e acetato `0`; no ponto `-4`, o crescimento diminui e surge uma nova secreção. Entregar essa secreção por um identificador ou nome curto suportado pela tabela.

### Mission 24 — Export Capacity Thresholds
**Tema:** curva de sensibilidade de uma capacidade de exportação, distinção entre upper bound não-binding e binding e ativação sequencial de rotas compensatórias.  
**Explica:** um upper bound pode existir sem alterar o ótimo enquanto o fluxo realizado ficar abaixo do cap. Quando a solução atinge o cap, uma restrição adicional pode redirecionar fluxos para outras secreções. A ordem de aparecimento das rotas deve ser inferida da curva completa.  
**Como passar:** depois da Missão 23, usar `pFBA`, objetivo `BIOMASS_Ecoli_core_w_GAM`, todos os genes ativos e ambiente-base completamente default. No `Bound Sweep Setup`, selecionar o upper bound de `EX_co2_e` e os valores `25`, `20`, `10`, `0`. Em `Production Flux`, selecionar `EX_co2_e`, `EX_for_e` e `EX_ac_e`. O relatório deve registar biomassa, uptake de glucose e oxigénio, os três fluxos acompanhados e os diagnósticos pFBA em cada linha. O cap `25` é não-binding; em `20`, CO₂ atinge o cap e surge a primeira secreção compensatória, mantendo acetato ausente; em `10`, acetato também aparece. Entregar a primeira rota compensatória suportada pela tabela.

## Lab 9 — Dr. Smith

### Mission 25 — Context-Dependent Gene Essentiality
**Tema:** essencialidade genética operacional dependente do ambiente, avaliada através de uma matriz controlada de oxigénio e genótipo.  
**Explica:** o efeito de um knockout não é uma propriedade universal do gene. A disponibilidade de rotas alternativas muda com o ambiente, pelo que o mesmo knockout pode ser quase neutro num contexto e impedir o crescimento previsto noutro.  
**Como passar:** depois da Missão 24, usar FBA com objetivo `BIOMASS_Ecoli_core_w_GAM` e construir, por qualquer ordem, quatro runs visíveis: wild type aeróbio, knockout aeróbio de `b3956 / ppc`, wild type com apenas o lower bound de `EX_o2_e` fechado e o mesmo knockout nesse meio anaeróbio. Manter todos os restantes bounds default. O relatório exige biomassa, glucose, oxigénio e diagnósticos FBA numericamente medidos, calcula a retenção do knockout dentro de cada contexto e preserva a matriz após tentativas inválidas. Entregar o contexto de oxigénio em que o knockout apresenta o defeito de crescimento mais severo, sem transformar a conclusão numa afirmação universal sobre o gene.

### Mission 26 — Genotype–Environment Interaction Curve
**Tema:** comparação de duas curvas de resposta e identificação de um threshold de interação entre genótipo e ambiente.  
**Explica:** a diferença entre wild type e knockout pode permanecer pequena ao longo de várias capacidades positivas de oxigénio e surgir abruptamente quando a rota ambiental alternativa é completamente removida. Um lower bound define capacidade de uptake; o primeiro ponto pode ser não-binding quando o fluxo realizado é inferior à capacidade.  
**Como passar:** depois da Missão 25, usar FBA com objetivo `BIOMASS_Ecoli_core_w_GAM`, ambiente-base completamente default e executar dois sweeps do lower bound de `EX_o2_e` com valores `-25`, `-10`, `-1`, `0`: um com todos os genes ativos e outro com apenas `b3956 / ppc` desligado. O relatório exige crescimento, glucose, oxigénio e diagnósticos FBA numéricos em todas as linhas, associa os pontos pelo bound e preserva curvas válidas após tentativas inválidas. O knockout deve manter mais de 90% do crescimento wild type nos três valores negativos, enquanto no valor `0` o wild type permanece viável e o knockout colapsa. Entregar o lower-bound testado que suporta esse threshold, inferido das duas curvas.

## Lab 10 — Dr. Ribeiro, Dr. Li and Dr. Chen

### Mission 27 — Metabolic Bypass Rescue
**Tema:** resgate metabólico por suplementação ambiental sem restauração da reação genética bloqueada.  
**Explica:** uma perturbação ambiental pode contornar operacionalmente a consequência de um knockout no modelo. Um resgate de crescimento não repara o gene nem reativa a reação desativada pela GPR; apenas demonstra que existe um bypass sob o meio, objetivo, bounds e candidatos testados.  
**Como passar:** depois da Missão 26, usar `pFBA` com objetivo `BIOMASS_Ecoli_core_w_GAM`. Registar uma referência wild type e uma referência com apenas `b0720 / gltA` desligado, ambas no meio completamente default. Depois manter esse knockout e abrir individualmente apenas o lower bound de `EX_akg_e`, `EX_pyr_e`, `EX_succ_e`, `EX_fum_e` e `EX_mal__L_e`, sem alterar glucose, oxigénio ou outros bounds. O relatório acumula os sete runs, exige `CS` desativada nos trials e preserva evidência válida após tentativas inválidas. Entregar o candidato que restaura crescimento previsto mantendo citrate synthase desativada.

### Mission 28 — Bypass Dependency Mapping
**Tema:** dependência mecanística de um resgate metabólico por suplementação.  
**Explica:** disponibilidade externa de um metabolito não equivale a acesso metabólico. O resgate por 2-oxoglutarato depende da função de transporte que permite a sua captação enquanto `CS` permanece desativada.  
**Como passar:** depois da Missão 27, usar `pFBA`, objetivo `BIOMASS_Ecoli_core_w_GAM`, manter `b0720 / gltA` desligado e abrir apenas `EX_akg_e`. Registar ou reutilizar a referência resgatada e testar separadamente um segundo knockout entre `b2587`, `b1761`, `b0728`, `b3236` e `b3403`. O relatório exige crescimento, uptake de 2-oxoglutarato e reações desativadas pela GPR, preservando evidência válida após tentativas inválidas. Entregar o knockout que elimina simultaneamente a captação do suplemento e o crescimento resgatado.


### Mission 29 — Isoenzyme Redundancy Screen
**Tema:** redundância funcional, lógica GPR `OR` e interação sinteticamente letal.  
**Explica:** um knockout individual pode ser fenotipicamente neutro quando outra isoenzima mantém a reação ativa. A remoção conjunta das duas alternativas pode revelar uma dependência não aditiva que não era visível nos singles.  
**Como passar:** depois da Missão 28, usar `pFBA`, objetivo `BIOMASS_Ecoli_core_w_GAM` e ambiente aeróbio completamente default. Registar uma referência wild type; os seis single knockouts `b0118`, `b1276`, `b1723`, `b3916`, `b1676` e `b1854`; e os três double knockouts correspondentes `b0118+b1276`, `b1723+b3916` e `b1676+b1854`. O relatório acumula dez runs por qualquer ordem, valida a GPR, calcula retenções e preserva evidência válida após tentativas inválidas. Entregar o par em que ambos os singles mantêm crescimento, mas o double knockout elimina o crescimento previsto.

### Mission 30 — Redundancy Breakdown Threshold
**Tema:** estabilidade ambiental de uma relação de redundância, curvas genótipo × oxigénio e distinção entre crescimento zero e estado `INFEASIBLE`.  
**Explica:** uma interação genética observada num meio não é automaticamente estável quando a capacidade respiratória muda. Os single knockouts podem continuar a acompanhar o wild type enquanto o double knockout perde progressivamente retenção e, num threshold testado, deixa de possuir qualquer solução admissível. `INFEASIBLE` não é um valor numérico de biomassa e nunca deve ser convertido em `0.000`.  
**Como passar:** depois da Missão 29, usar `pFBA`, objetivo `BIOMASS_Ecoli_core_w_GAM` e ambiente-base completamente default. No `Bound Sweep Setup`, selecionar o lower bound de `EX_o2_e` e o preset dedicado `-30`, `-10`, `-5`, `-2`. Registar quatro curvas em qualquer ordem: wild type, apenas `b1723 / pfkB`, apenas `b3916 / pfkA` e o double knockout exato `b1723+b3916`. O relatório exige glucose, oxigénio e diagnósticos pFBA em todas as linhas viáveis, preserva explicitamente o estado inviável sem fabricar zeros e mantém curvas válidas após tentativas erradas. Entregar o lower bound testado em que apenas o double knockout se torna inviável, enquanto os três controlos permanecem viáveis.

### Mission 31 — Environmental Suppression Matrix
**Tema:** supressão ambiental de um fenótipo sinteticamente letal, matriz genótipo × fonte de carbono e distinção entre uptake e resgate de crescimento.  
**Explica:** a classificação de uma interação genética depende do ambiente testado. Um substrato pode ser captado numa solução viável com biomassa igual a zero, pelo que uptake positivo não demonstra, por si só, supressão do defeito. Uma fonte alternativa pode restaurar crescimento sem reativar as reações eliminadas pela GPR.  
**Como passar:** depois da Missão 30, usar `pFBA`, objetivo `BIOMASS_Ecoli_core_w_GAM`, fechar o lower bound de `EX_glc__D_e` e abrir exatamente uma fonte entre `EX_fru_e`, `EX_pyr_e`, `EX_succ_e` e `EX_glu__L_e`, mantendo oxigénio e restantes bounds default. Para cada fonte, registar um wild type e o double knockout exato `b0118+b1276`, totalizando oito runs por qualquer ordem. O relatório exige crescimento, uptake da fonte, oxigénio, diagnósticos pFBA e `ACONTa`/`ACONTb` desativadas apenas no double knockout; preserva evidência após tentativas inválidas. Entregar a fonte testada que restaura forte retenção de crescimento sem restaurar as duas reações de aconitase.


### Mission 32 — Respiratory Complex Cut-Set
**Tema:** lógica GPR aninhada, complexos proteicos alternativos e identificação de um cut set respiratório dentro do conjunto testado.  
**Explica:** cada ramo de `CYTBD` exige duas subunidades ligadas por `AND`, enquanto os dois complexos completos são alternativas ligadas por `OR`. Quebrar apenas um ramo não desativa a reação; é necessário tornar ambos os ramos incompletos. Oxigénio disponível no meio não garante uptake se a função respiratória necessária for removida.  
**Como passar:** depois da Missão 31, usar `pFBA`, objetivo `BIOMASS_Ecoli_core_w_GAM` e ambiente aeróbio completamente default. Registar por qualquer ordem wild type, `b0978`, `b0733`, `b0978+b0979`, `b0733+b0734` e `b0978+b0733`. Os cinco controlos devem manter crescimento próximo de `0.874`, uptake de oxigénio próximo de `21.799` e `CYTBD` disponível. O par cruzado deve permanecer viável com crescimento próximo de `0.212`, desativar `CYTBD`, reduzir uptake de oxigénio a zero e mostrar secreção de acetato, etanol e formato. Entregar o par testado que quebra um componente obrigatório de cada ramo, sem generalizar a conclusão a todos os pares possíveis.

### Mission 33 — Reference-State Adjustment Footprint
**Tema:** ROOM, estado de referência explícito e pegada de ajuste após uma perturbação.
**Explica:** o impacto funcional de um knockout depende do estado de fluxo anterior. ROOM minimiza o número de alterações significativas relativamente a uma referência wild type pFBA pré-knockout; o seu score não é biomassa, fluxo absoluto total nem contagem de reações ativas. Uma reação pode ficar desativada pela GPR sem exigir alteração de fluxo quando já transportava fluxo zero na referência. A formulação inteira é resolvida com SciPy/HiGHS e limite de segurança de 12 segundos para evitar bloqueios do jogo.
**Como passar:** depois da Missão 32, construir quatro runs visíveis em qualquer ordem. No contexto aeróbio completamente default, registar uma referência wild type com `pFBA` e o mutante exato `b0978+b0733` com `ROOM`. Repetir o par fechando apenas o lower bound de `EX_o2_e`. Todos usam `BIOMASS_Ecoli_core_w_GAM`. Cada resultado ROOM deve provar que usou uma referência wild type pFBA, pré-knockout e no mesmo ambiente, com `delta=0.03`, `epsilon=0.001` e formulação inteira. A referência aeróbia deve ter `CYTBD` ativa e score ROOM positivo; a referência com oxigénio fechado deve ter `CYTBD` com fluxo zero e score ROOM zero, mantendo `CYTBD` desativada nos dois mutantes. Entregar a propriedade do estado de referência que explica a pegada nula, em vez de responder apenas com o contexto, método ou genes.

### Mission 34 — Shared-Subunit Equivalence Audit
**Tema:** genes partilhados entre várias GPR, diferença entre número de knockouts e número de reações afetadas, e equivalência ao nível das reações.  
**Explica:** um único gene pode participar em várias reações e, por isso, desativar mais do que uma GPR. Em sentido inverso, dois knockouts dentro de um complexo já quebrado podem continuar a afetar apenas uma reação. Genótipos distintos podem impor o mesmo conjunto de bounds de reação e gerar o mesmo problema metabólico, sem serem geneticamente idênticos.  
**Como passar:** depois da Missão 33, usar `pFBA`, objetivo `BIOMASS_Ecoli_core_w_GAM` e ambiente aeróbio completamente default. Registar por qualquer ordem wild type, `b0114`, `b0726`, `b0726+b0727`, `b0116` e `b0114+b0726`. O resultado visível deve expor o conjunto completo de reações desativadas pela GPR. `b0726` e `b0726+b0727` devem desativar apenas `AKGDH` e produzir resultados correspondentes; `b0116` e `b0114+b0726` devem desativar `AKGDH` e `PDH` e apresentar crescimento, uptake de oxigénio, formato, fluxo absoluto total e contagem de reações ativas correspondentes. Entregar a relação ao nível das reações entre o single partilhado e o double dividido.

### Mission 35 — E. coli Final Systems Certification
**Tema:** missão final integradora do modelo de *E. coli*: aprovação multicritério de um design, robustez ambiental por curvas de oxigénio e auditoria de viabilidade perante mudança da função objetivo.  
**Explica:** uma intervenção não deve ser escolhida apenas pelo maior produto; crescimento retido e impacto GPR também contam. Genótipos mecanisticamente diferentes podem convergir para o mesmo painel fenotípico sob limitação ambiental, sem se tornarem mecanicamente equivalentes. Maximizar diretamente um produto pode ainda selecionar um ótimo sem crescimento.  
**Como passar:** depois da Missão 34, completar três secções. (A) Com `pFBA`, objetivo `BIOMASS_Ecoli_core_w_GAM`, ambiente aeróbio completamente default e painel exato `EX_for_e`, `EX_ac_e`, `EX_etoh_e`, registar wild type, `b0114`, `b0726` e `b0116`. O design aprovado tem de cumprir simultaneamente formato >= `7.5`, retenção de crescimento >= `90%` e no máximo uma reação desativada pela GPR. (B) Registar dois Bound Sweeps visíveis para `b0114` e `b0116`, sempre com pFBA/biomassa, base ambiental default, variável `EX_o2_e` lower bound e preset `Final oxygen convergence` com `-30,-10,-5,-2`; determinar o primeiro ponto testado de convergência fenotípica sustentada, mantendo distintos os conjuntos GPR. (C) Voltar ao ambiente default, usar `b0114`, `pFBA` e objetivo `EX_for_e`, comparando o máximo direto de formato com o run de biomassa já guardado. Entregar três conclusões curtas no menu final. Ao concluir, a progressão passa a desbloquear a skin `Golden LabHero`, a capacidade lógica `golden_lab` e o futuro modelo `yeast_iMM904`; a skin não é equipada automaticamente.

## Golden Lab — Yeast iMM904

Após a certificação de *E. coli*, o jogo introduz o segundo modelo metabólico, `yeast_iMM904`, sem substituir o simulador original. No Normal, M35 desbloqueia a Golden Lab, a skin `Golden LabHero` e o modelo de levedura. No Easy, a progressão equivalente para acesso à Golden Lab ocorre após M27; a skin dourada continua exclusiva da conclusão real da M35 Normal.

A seleção do modelo é explícita através de `model_id`: o computador original usa `ecoli_core` e o computador da Golden Lab usa `yeast_iMM904`. O mesmo contrato estruturado é usado no desktop e no browser. O backend mantém templates em cache, mas cada pedido trabalha sobre uma cópia isolada antes de aplicar objetivo, bounds ou knockouts.

O iMM904 incluído no projeto possui aproximadamente 1577 reações, 164 exchanges e 905 genes, com objetivo default `BIOMASS_SC5_notrace`. O simulador de levedura expõe FBA/pFBA, valida objetivo, genes e exchanges contra o catálogo real e mostra uma preview canónica das alterações registadas. O Bound Sweep é model-aware e é utilizado pelas Missões 36 e 40.

A sequência Normal da Golden Lab é:

```text
Vale -> M36
Voss -> M37
Umbra -> M38
Morbus -> M39
Mortis -> M40
```

### Mission 36 — Oxygen-Capped Fermentation Onset
**NPC:** Vale.  
**Tema:** interação entre disponibilidade de carbono, capacidade respiratória fixa e início de secreção fermentativa.  
**Explica:** uma constraint que não é alterada diretamente pode tornar-se binding quando outra entrada aumenta. No iMM904 default, o lower bound de `EX_o2_e` permanece fixo em `-2`, enquanto a disponibilidade de glucose é variada. O primeiro ponto em que a solução usa toda a capacidade de O₂ e passa a secretar etanol deve ser inferido da curva visível.  
**Como passar:** usar `pFBA`, objetivo `BIOMASS_SC5_notrace`, wild type e ambiente base completamente default. Acompanhar exatamente `EX_etoh_e` e `EX_co2_e`. Primeiro registar a referência default; depois executar um Bound Sweep do lower bound de `EX_glc__D_e` com `-0.5`, `-1`, `-2`, `-10`. A referência deve coincidir com a linha `-10` dentro da tolerância. A curva mostra aproximadamente O₂ `1.414` e etanol `0` em `-0.5`, e O₂ `2.000` com etanol positivo já em `-1`. Entregar o primeiro lower bound testado que satisfaz simultaneamente as duas condições.

### Mission 37 — Fermentation Redundancy Cut Set
**NPC:** Voss.  
**Tema:** redundância genética e identificação de um cut set funcional na fermentação da levedura.  
**Explica:** perturbar uma única alternativa genética pode ser compensado por outras isoenzimas; a conclusão deve ser baseada numa série controlada de single, double e triple knockouts, e não no nome de um gene isolado.  
**Como passar:** usar `pFBA`, objetivo `BIOMASS_SC5_notrace`, ambiente completamente default e acompanhar exatamente `EX_etoh_e` e `EX_succ_e`. Deixar Bound Sweep desligado. Registar, por qualquer ordem, WT, `PDC1`, `PDC1+PDC5`, `PDC1+PDC6`, `PDC5+PDC6` e `PDC1+PDC5+PDC6`. Comparar crescimento e os fluxos acompanhados para identificar o conjunto testado cuja remoção conjunta quebra a redundância fermentativa.

### Mission 38 — Background-Dependent Compensation Audit
**NPC:** Umbra.  
**Tema:** vulnerabilidade genética dependente do background e comparação de efeitos condicionais.  
**Explica:** o mesmo knockout pode ser quase neutro num background e tornar-se muito mais importante depois de outra via já ter sido perturbada. A missão exige comparar o candidato sozinho com WT e o mesmo candidato sobre o background `PDC1+PDC5+PDC6`, evitando concluir a partir de um único genótipo.  
**Como passar:** usar `pFBA`, objetivo `BIOMASS_SC5_notrace`, ambiente default, Bound Sweep desligado e acompanhar exatamente `EX_etoh_e`, `EX_succ_e`, `EX_pyr_e`. Registar WT, `FRD1`, `MAE1`, `PDC1+PDC5+PDC6`, `PDC1+PDC5+PDC6+FRD1` e `PDC1+PDC5+PDC6+MAE1`. Comparar os pares controlados e entregar o candidato cujo grande efeito é específico do background alterado.

### Mission 39 — Pathway Bypass Rescue
**NPC:** Morbus.  
**Tema:** rescue metabólico por suplementação e posição de um metabolito numa via bloqueada.  
**Explica:** tornar um metabolito externamente disponível não demonstra resgate. É necessário provar uptake real e recuperação fenotípica na mesma solução. A posição do suplemento relativamente ao passo bloqueado distingue um precursor de um verdadeiro bypass.  
**Como passar:** usar `pFBA`, objetivo `BIOMASS_SC5_notrace` e o genótipo fixo `PDC1+PDC5+PDC6+FRD1`. Acompanhar exatamente `EX_etoh_e`, `EX_succ_e`, `EX_pyr_e` e manter Bound Sweep desligado. Registar quatro ambientes: default; abrir apenas o lower bound de `EX_pyr_e`; abrir apenas `EX_etoh_e`; abrir apenas `EX_acald_e`. Comparar cada suplemento com a referência, verificando uptake, crescimento e recuperação de etanol. Entregar o suplemento testado que funciona como bypass.

### Mission 40 — Final Rescue Robustness Certification
**NPC:** Mortis.  
**Tema:** robustez de um rescue através de curvas ambientais emparelhadas.  
**Explica:** uma intervenção que funciona num único meio não está automaticamente certificada como robusta. A missão final compara duas curvas de glucose com o mesmo genótipo e protocolo, diferindo apenas na disponibilidade do bypass identificado na missão anterior.  
**Como passar:** usar `pFBA`, objetivo `BIOMASS_SC5_notrace`, genótipo fixo `PDC1+PDC5+PDC6+FRD1` e acompanhar exatamente `EX_etoh_e`, `EX_succ_e`, `EX_pyr_e`. Executar dois Bound Sweeps do lower bound de `EX_glc__D_e` com `-0.5`, `-1`, `-2`, `-10`: uma curva com ambiente base completamente default e outra com o mesmo setup, abrindo apenas o lower bound de `EX_acald_e`. Comparar ponto a ponto e entregar os lower bounds testados em que o bypass constitui um rescue completo segundo os critérios da missão.

## Progressão final e exploração opcional

A campanha Normal termina na M40; a campanha Easy termina na M36. Final Results é apresentado quando a missão final da rota selecionada é concluída e pode ser reaberto com **F**.

O Golden Egg é um elemento opcional de exploração, separado dos validators das missões. Quando é recolhido antes do fim da campanha, o estado `golden_egg_collected` é persistido e a recompensa é atribuída uma única vez (Normal: +3 Gold Keys; Easy: +1 Gold Key). A progression gate dependente do ovo abre apenas quando esse estado é verdadeiro; concluir M35/M40 por si só não satisfaz essa condição.
