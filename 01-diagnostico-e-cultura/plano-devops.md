# Plano DevOps — Diagnóstico e Cultura (Fase 1)

> Antes de tocar em qualquer tecnologia, este documento mapeia como a CloudAWSPizza trabalha hoje, define onde ela precisa chegar e traça o caminho — em cultura, processos e governança — para sair de um lugar do outro. É o "porquê" por trás de todas as decisões técnicas das fases seguintes.

## 1. Diagnóstico do cenário atual

A CloudAWSPizza nasceu como uma pizzaria familiar e cresceu apoiada em tecnologia, mas o sistema de pedidos ainda roda como uma aplicação monolítica única, instalada em um servidor físico dentro de um pequeno datacenter local. O crescimento trouxe os sintomas clássicos de uma organização que escalou o negócio sem escalar a forma de trabalhar:

### 1.1 Times isolados, sem visibilidade compartilhada

Desenvolvimento e operação são times separados, com backlogs, ferramentas e até vocabulário diferentes. Quem escreve o código não é quem sobe para produção, e quem sobe para produção não participou do design da funcionalidade. O resultado é o clássico "jogar por cima do muro": dev entrega um pacote, ops tenta encaixá-lo em produção sem contexto, e quando algo quebra ninguém tem a visão completa do problema.

### 1.2 Deploys manuais, arriscados e pouco frequentes

Não existe pipeline de build, teste ou deploy. Subir uma versão nova significa um funcionário logar via SSH no servidor, parar o processo, copiar arquivos manualmente e reiniciar o serviço — geralmente à noite, torcendo para não haver pedidos em andamento no momento do restart. Como o processo é manual, arriscado e estressante, a equipe evita fazer deploys: o que deveria ser um evento trivial e frequente virou um evento raro e temido, o que por sua vez faz cada deploy acumular mudanças demais, aumentando ainda mais o risco. É um ciclo vicioso.

### 1.3 Zero automação de testes ou infraestrutura

Não há suíte de testes automatizados — a validação é manual, feita "clicando no sistema" antes de cada deploy, quando há tempo. A infraestrutura também não é automatizada: o servidor foi configurado manualmente ao longo dos anos, ninguém tem certeza de quais pacotes, versões e configurações estão realmente ativos nele, e recriar esse ambiente do zero hoje seria um processo de dias, dependente de conhecimento tácito de uma ou duas pessoas.

### 1.4 Monitoramento reativo

Não existe observabilidade proativa. Não há dashboards, alertas ou métricas de saúde do sistema. Os problemas são descobertos quando um cliente liga reclamando que não conseguiu fazer um pedido, ou quando um funcionário percebe que o sistema "está lento" sem conseguir dizer por quê. O tempo entre o início de um incidente e sua detecção (e, consequentemente, sua resolução) é alto e imprevisível.

### 1.5 Acoplamento forte do monólito — o ponto mais crítico

O problema estrutural mais grave, e o que mais afeta diretamente a receita, é o acoplamento forte da aplicação: **se o módulo de pagamento travar, o pedido inteiro trava junto**. Hoje, criar um pedido chama diretamente e de forma síncrona a lógica de pagamento — na mesma thread, no mesmo processo, sem nenhum isolamento de falha. Isso significa que:

- Uma instabilidade momentânea no processador de pagamento (timeout de gateway, lentidão de rede) derruba a capacidade de *aceitar pedidos*, não só de cobrá-los.
- Não há como escalar o processamento de pedidos e o processamento de pagamentos de forma independente, mesmo que tenham perfis de carga e de criticidade diferentes.
- Qualquer bug ou deploy no código de pagamento é, por definição, um risco para todo o fluxo de pedidos.

Esse acoplamento é o principal driver técnico por trás das decisões de arquitetura da Fase 2 e da evolução para microsserviços assíncronos na Fase 3: a meta ali não é "usar microsserviços porque é moderno", mas especificamente romper essa dependência síncrona para que uma falha de pagamento nunca mais derrube a captura de um pedido.

## 2. Objetivos mensuráveis

Diagnosticar sem medir é só reclamar com mais passos. Definimos metas concretas usando as **quatro métricas DORA** (DevOps Research and Assessment) como referência, por serem o padrão de mercado para medir performance de entrega de software, mais duas métricas complementares específicas do nosso contexto.

| Métrica | Situação atual (estimada) | Meta em 6 meses | Meta em 12 meses |
|---|---|---|---|
| **Deployment Frequency** (frequência de deploy) | ~1x por mês, manual | 1x por semana | Múltiplas vezes por semana (sob demanda) |
| **Lead Time for Changes** (tempo do commit até produção) | Dias a semanas | < 1 dia | < 1 hora |
| **Change Failure Rate** (% de deploys que causam incidente) | Desconhecida, estimada alta (sem medição) | < 15% | < 10% |
| **Time to Restore Service / MTTR** (tempo médio de recuperação) | Horas (depende de alguém perceber o problema) | < 1 hora | < 15 minutos |
| Cobertura de testes automatizados | 0% | ≥ 60% nos módulos críticos (pedidos, pagamento) | ≥ 80% |
| Incidentes causados por acoplamento pagamento→pedido | Recorrente | Isolado via arquitetura assíncrona (Fase 3) | Zero |

Essas metas colocam a CloudAWSPizza, segundo a classificação DORA, saindo de um perfil **"Low performer"** para um perfil **"High/Elite performer"** ao longo de aproximadamente um ano — não da noite para o dia, e sim através das etapas descritas a seguir.

## 3. Plano de ação em etapas

### 3.1 Curto prazo (0–3 meses) — parar de sangrar

Foco em reduzir risco imediato e estabelecer as bases de automação, sem ainda mexer na arquitetura da aplicação.

- **Versionar tudo**: garantir que todo o código-fonte esteja em um repositório Git compartilhado (hoje parte do conhecimento vive só na cabeça de quem mantém o servidor).
- **Escrever os primeiros testes automatizados** para o fluxo crítico: criação de pedido e processamento de pagamento — os módulos mais sensíveis e os que mais geram incidentes.
- **Implementar um pipeline de CI básico**: a cada push, rodar lint e a suíte de testes automaticamente. Ainda sem deploy automático — o objetivo aqui é dar visibilidade e confiança, não velocidade.
- **Criar um runbook de deploy manual**, documentando o processo atual passo a passo, para reduzir a dependência de conhecimento tácito enquanto a automação não chega.
- **Instrumentar logs mínimos** de erros de pagamento e de pedido, para pelo menos começar a enxergar os incidentes que hoje só chegam por reclamação de cliente.

### 3.2 Médio prazo (3–6 meses) — automatizar a entrega

- **Pipeline de CD completo**: deploy automatizado para um ambiente de staging a cada merge na branch principal, com promoção para produção via aprovação manual (deploy semi-automatizado).
- **Infraestrutura como código**: descrever a infraestrutura atual (ou a nova, já pensando na AWS da Fase 2) em Terraform, eliminando a configuração manual de servidor e tornando o ambiente reproduzível e auditável.
- **Formar os squads multidisciplinares** (detalhado na seção 4), encerrando a separação rígida entre "time de dev" e "time de ops".
- **Instituir observabilidade básica**: dashboards de métricas de aplicação e infraestrutura, com alertas automáticos para os principais sinais de saúde (taxa de erro, latência, disponibilidade) — substituindo o monitoramento reativo por um proativo.
- **Iniciar a quebra do monólito**: começar a extrair o módulo de pagamento como serviço independente, comunicando-se de forma assíncrona com o módulo de pedidos (ver Fase 3), removendo o acoplamento síncrono identificado no diagnóstico.

### 3.3 Longo prazo (6–12 meses) — consolidar a cultura DevOps

- **Deploy contínuo sob demanda**: qualquer mudança aprovada em code review e que passe no pipeline pode ir para produção no mesmo dia, sem etapas manuais de promoção.
- **Observabilidade completa**: tracing distribuído entre os serviços (especialmente relevante após a quebra do monólito), dashboards de negócio (pedidos/hora, taxa de conversão, tempo médio de entrega) além dos técnicos.
- **Cultura de melhoria contínua institucionalizada**: métricas DORA revisadas mensalmente pelos squads, com ações concretas geradas a partir delas — não apenas números em um dashboard que ninguém olha.
- **Disaster recovery testado**: simulações regulares de falha (incluindo falhas induzidas do módulo de pagamento) para validar que o isolamento arquitetural realmente funciona sob estresse.

## 4. Mudanças de governança

Automação sem mudança de cultura resolve metade do problema. A outra metade é como as pessoas se organizam e se relacionam com falhas.

### 4.1 Squads multidisciplinares (dev + ops + produto)

Substituímos os times isolados por squads que reúnem, em uma única equipe, desenvolvimento, operação e uma voz de produto — cada squad dono de uma fatia vertical do sistema (por exemplo, um squad "Pedidos", outro "Pagamentos"), responsável do design ao monitoramento em produção. Isso elimina o "jogar por cima do muro": quem escreve o código também participa do deploy e é acionado se ele quebrar, o que naturalmente melhora a qualidade do que é escrito e reduz o tempo de resposta a incidentes. A voz de produto garante que decisões técnicas (como a própria quebra do monólito) sejam sempre conectadas ao impacto para o cliente que está tentando pedir uma pizza.

### 4.2 Blameless post-mortems

Todo incidente relevante (por exemplo, uma indisponibilidade causada pelo módulo de pagamento travando o fluxo de pedidos) gera um post-mortem sem culpados: o objetivo é entender as condições sistêmicas que permitiram a falha — não apontar quem "causou" o problema. Isso é essencial para uma cultura DevOps saudável, porque só funciona se as pessoas se sentirem seguras para reportar problemas e falar abertamente sobre erros; time com medo de punição esconde informação, e informação escondida é exatamente o que perpetua incidentes recorrentes como os do acoplamento pagamento→pedido.

### 4.3 Rituais ágeis

- **Dailies**: alinhamento rápido e diário dentro de cada squad, focado em bloqueios e continuidade do trabalho.
- **Sprint planning**: priorização conjunta entre dev, ops e produto, evitando que decisões técnicas de infraestrutura sejam feitas isoladamente de decisões de negócio (e vice-versa).
- **Retrospectivas**: revisão periódica não só de entregas, mas das métricas DORA do squad — se o lead time subiu ou o change failure rate piorou, a retro é o espaço para investigar o porquê e agir.

## 5. Métricas de acompanhamento

O acompanhamento contínuo usa as **quatro métricas DORA** como painel principal de saúde do processo de entrega:

- **Deployment Frequency** — com que frequência conseguimos colocar código em produção com segurança. Quanto maior, mais rápido o negócio recebe valor e mais cedo problemas são detectados (mudanças menores e mais frequentes são mais fáceis de diagnosticar).
- **Lead Time for Changes** — tempo entre um commit ser feito e ele estar rodando em produção. Mede diretamente o atrito do nosso próprio processo de entrega.
- **Change Failure Rate** — percentual de deploys que resultam em degradação de serviço ou precisam de correção emergencial. É o termômetro de qualidade do pipeline e dos testes.
- **MTTR (Mean Time to Restore)** — tempo médio entre a detecção de um incidente e sua resolução. Mede a capacidade de resposta do time e a qualidade da observabilidade.

Essas quatro métricas serão revisadas mensalmente pelos squads e trimestralmente pela liderança, servindo como critério objetivo de progresso da transformação DevOps — e como ponte direta para a Fase 2: a arquitetura em nuvem proposta a seguir é desenhada, entre outras coisas, para tornar essas metas alcançáveis (deploys mais seguros via ambientes isolados, escalabilidade independente por componente, e observabilidade nativa via CloudWatch).
