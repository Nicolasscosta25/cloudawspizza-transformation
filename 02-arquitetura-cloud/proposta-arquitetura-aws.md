# Proposta de Arquitetura em Nuvem — AWS (Fase 2)

> Com o "como trabalhamos" definido na Fase 1, este documento define "onde e com o quê construir": a arquitetura AWS-alvo para a CloudAWSPizza, incluindo o raciocínio por trás de cada escolha de serviço, rede, segurança e custo. Essa arquitetura guia diretamente o provisionamento real via Terraform feito na Fase 4.

## 1. Provedor escolhido: AWS

Optamos pela **Amazon Web Services (AWS)** como provedor de nuvem para a CloudAWSPizza pelos seguintes motivos:

- **Maturidade e abrangência de serviços**: AWS oferece, dentro de um único ecossistema integrado, tudo que este case precisa — computação (EC2), banco de dados gerenciado (RDS), armazenamento de objetos (S3), funções serverless (Lambda), rede isolada (VPC) e observabilidade (CloudWatch) — sem depender de múltiplos fornecedores.
- **Free Tier generoso**, adequado ao estágio atual da CloudAWSPizza (uma pizzaria de porte pequeno/médio migrando de um servidor local), permitindo validar a arquitetura com custo mínimo antes de comprometer orçamento maior.
- **Padrão de mercado**: é o provedor mais adotado, o que facilita contratação, documentação e suporte da comunidade — relevante para uma empresa que está construindo sua capacidade técnica interna do zero.
- **Ambiente de estudo/laboratório**: este case foi construído e provisionado (Fase 4) em um ambiente **AWS Academy Learner Lab**, que tem particularidades de permissão tratadas na seção 5.1 — mas as decisões de arquitetura aqui descritas são válidas e portáveis para uma conta AWS de produção padrão.

## 2. Modelos de serviço por componente

Cada componente da CloudAWSPizza foi mapeado para o modelo de serviço (IaaS, PaaS, FaaS, SaaS gerenciado) que melhor equilibra controle, esforço operacional e custo:

| Componente | Serviço AWS | Modelo | Justificativa |
|---|---|---|---|
| Aplicação (API de pedidos/pagamentos) | EC2 (t3.micro) | **IaaS** | Controle total do runtime, necessário no estágio atual do case (aplicação FastAPI hospedada diretamente); elegível ao Free Tier. |
| Banco de dados | RDS MySQL (db.t3.micro) | **PaaS / gerenciado** | Backups, patching e failover geridos pela AWS — a equipe não deveria estar operando MySQL manualmente (ver seção 4). |
| Notificação de novos pedidos | Lambda | **FaaS / serverless** | Carga de trabalho event-driven, esporádica (um pedido = uma notificação); não faz sentido manter servidor dedicado rodando 24/7 para isso. |
| Arquivos estáticos (assets do site, comprovantes, etc.) | S3 | **Armazenamento de objetos gerenciado** | Durável, escalável e barato para conteúdo estático, sem servidor para gerenciar. |
| Rede | VPC | **Infraestrutura de rede gerenciada** | Isolamento lógico entre o que é público (aplicação) e o que é privado (dados). |
| Monitoramento | CloudWatch | **Observabilidade gerenciada** | Métricas e alarmes nativos da instância EC2, sem precisar operar stack de monitoramento própria nesta fase. |
| Identidade/permissões | IAM | **Gerenciado** | Controle de acesso entre os serviços acima (ver seção 5.1 sobre o uso do LabRole no ambiente de estudo). |

A lógica geral é: **IaaS onde ainda precisamos de controle direto sobre a aplicação** (EC2, refletindo o estágio de migração do monólito), **PaaS onde operar o serviço nós mesmos não agrega valor** (RDS), e **FaaS onde a carga é esporádica e orientada a eventos** (Lambda) — evitando pagar por capacidade ociosa.

## 3. Estrutura de rede

A rede é desenhada em torno de uma **VPC** (Virtual Private Cloud) própria, na região **us-east-1**, com sub-redes públicas e privadas para separar o que precisa ser alcançável pela internet do que não precisa.

### 3.1 Componentes de rede

- **VPC**: bloco de endereços isolado logicamente, exclusivo da CloudAWSPizza.
- **Sub-rede pública**: hospeda a instância **EC2** da aplicação. Tem rota direta para a internet via **Internet Gateway**, permitindo que clientes acessem a API de pedidos e que a instância receba tráfego de entrada (portas 80/443) e administração (SSH restrito).
- **Sub-rede privada**: hospeda a instância **RDS MySQL**. Não tem rota para a internet — o banco de dados nunca é diretamente exposto, só é alcançável a partir da aplicação dentro da própria VPC.
- **Internet Gateway (IGW)**: anexado à VPC, é o único ponto de entrada/saída de tráfego para a internet, usado pela sub-rede pública.
- **Route Tables**: a tabela de rotas da sub-rede pública aponta `0.0.0.0/0` para o Internet Gateway; a tabela de rotas da sub-rede privada não tem rota para a internet, garantindo que o RDS permaneça inacessível externamente por padrão.

### 3.2 Diagrama da arquitetura

```
                                   Internet
                                       │
                                       │
                            ┌──────────▼──────────┐
                            │   Internet Gateway   │
                            └──────────┬──────────┘
                                       │
 ┌─────────────────────────────────────┼─────────────────────────────────────┐
 │  VPC (us-east-1)                    │                                     │
 │                                       │                                     │
 │   ┌───────────────────────────────────▼────────────────────────────────┐  │
 │   │  Sub-rede PÚBLICA                                                    │  │
 │   │                                                                       │  │
 │   │   ┌───────────────────────┐                                          │  │
 │   │   │   EC2 (t3.micro)      │◄── SG: 80/443 (público), 22 (restrito)   │  │
 │   │   │   Aplicação (API)     │                                          │  │
 │   │   └───────────┬───────────┘                                          │  │
 │   └───────────────┼──────────────────────────────────────────────────────┘  │
 │                   │ SG app → SG db, porta 3306                              │
 │   ┌───────────────▼──────────────────────────────────────────────────────┐  │
 │   │  Sub-rede PRIVADA (sem rota para a internet)                          │  │
 │   │                                                                        │  │
 │   │   ┌────────────────────────────┐                                      │  │
 │   │   │  RDS MySQL (db.t3.micro)   │  ◄── só aceita conexões da EC2       │  │
 │   │   └────────────────────────────┘                                      │  │
 │   └────────────────────────────────────────────────────────────────────────┘  │
 │                                                                                │
 │   ┌────────────────────┐      ┌────────────────────┐      ┌───────────────┐ │
 │   │  Lambda             │      │  S3                 │      │  CloudWatch   │ │
 │   │  (notificação de    │      │  (arquivos           │      │  (alarmes na  │ │
 │   │   novo pedido)      │      │   estáticos)          │      │   instância   │ │
 │   │  fora da VPC ou em   │      │  serviço regional      │      │   EC2)        │ │
 │   │  sub-rede própria    │      │  (fora da VPC)          │      │               │ │
 │   └─────────┬───────────┘      └─────────────────────┘      └───────────────┘ │
 │             │ invocada por evento (novo pedido)                                │
 │             └────────────────────────────────────────────────────────────────► notifica
 │                                                                                │
 └────────────────────────────────────────────────────────────────────────────────┘
```

*(S3 e Lambda são serviços regionais/gerenciados pela AWS e não residem "dentro" da VPC do mesmo jeito que EC2/RDS — representados aqui à parte para deixar clara a topologia lógica.)*

## 4. Estratégia de banco de dados

O banco de dados da CloudAWSPizza roda em **Amazon RDS para MySQL**, instância `db.t3.micro`, dentro da sub-rede privada.

### Por que gerenciado (RDS) em vez de self-hosted (MySQL na EC2)

- **Backups automatizados**: RDS realiza snapshots automáticos diários com retenção configurável, além de backups sob demanda antes de mudanças arriscadas — sem esse processo precisar ser escrito e mantido manualmente pela equipe.
- **Patching gerenciado**: atualizações de segurança do engine MySQL são aplicadas pela AWS em janelas de manutenção configuráveis, eliminando uma fonte recorrente de trabalho operacional manual (e de risco, se for esquecida — como no cenário de diagnóstico da Fase 1).
- **Menor superfície de erro humano**: no modelo atual (self-hosted, servidor físico), a configuração do banco depende de conhecimento tácito de quem o mantém. RDS reduz essa dependência ao padronizar a operação.
- **Ponto único de verdade sobre a saúde do banco**: métricas de CPU, conexões, IOPS e espaço em disco ficam disponíveis nativamente, integráveis ao CloudWatch — apoiando diretamente a meta de monitoramento proativo definida na Fase 1.
- **Isolamento de rede nativo**: por estar na sub-rede privada, o RDS só é alcançável pela EC2 da aplicação (via Security Group), nunca diretamente da internet.

O trade-off aceito é menor controle de baixo nível sobre o engine (por exemplo, acesso ao sistema operacional subjacente) — irrelevante para o estágio atual do projeto, onde previsibilidade operacional vale mais que customização profunda.

## 5. Segurança

### 5.1 IAM

O princípio orientador é **least privilege** (menor privilégio necessário): cada componente deve ter acesso apenas ao que precisa para funcionar, nada além disso.

> **Nota sobre o ambiente de estudo (AWS Academy Learner Lab)**: este case foi provisionado em um ambiente de laboratório acadêmico (AWS Academy Learner Lab), onde a criação de roles IAM customizadas é restrita pela política da conta — apenas as roles pré-provisionadas pelo laboratório (`LabRole` e o instance profile `LabInstanceProfile`) podem ser anexadas a recursos como EC2 e Lambda. Por isso, a infraestrutura da Fase 4 reutiliza `LabRole`/`LabInstanceProfile` em vez de criar roles customizadas por componente.
>
> Isso é uma adaptação **ao ambiente de laboratório**, não uma recomendação de arquitetura. **Em uma conta AWS de produção real**, a prática correta — e a que seria implementada — é criar roles de menor privilégio dedicadas por componente (ex.: uma role só para a EC2 da aplicação com permissão de leitura/escrita no S3 específico e nada mais; uma role só para a Lambda de notificação com permissão apenas de publicar a notificação necessária), evitando o uso de uma role ampla e compartilhada como `LabRole`.

### 5.2 Security Groups

Os Security Groups funcionam como firewall stateful por recurso, seguindo também o princípio de menor privilégio:

- **SG da aplicação (EC2)**: permite entrada nas portas **80/443** (HTTP/HTTPS, tráfego público de clientes) e **22** (SSH, restrito a um range de IP confiável — nunca `0.0.0.0/0` para administração).
- **SG do banco de dados (RDS)**: permite entrada **apenas na porta 3306 (MySQL)**, e apenas com origem no **Security Group da aplicação** — não a um range de IP, mas ao próprio SG, garantindo que só a instância EC2 da aplicação (e nada mais, nem mesmo outras instâncias na mesma VPC) consiga se conectar ao banco.

### 5.3 Criptografia

- **Em trânsito**: comunicação entre cliente e aplicação via HTTPS/TLS; comunicação entre aplicação e RDS dentro da VPC também deve usar conexão criptografada (SSL/TLS suportado nativamente pelo RDS MySQL).
- **Em repouso**: armazenamento criptografado no RDS (encryption at rest, usando as chaves gerenciadas pela AWS) e no S3 (server-side encryption habilitada por padrão nos buckets).

### 5.4 WAF (próximo passo)

Um **AWS WAF (Web Application Firewall)** na frente da aplicação (associado a um Application Load Balancer ou CloudFront) não está implementado neste MVP, mas é reconhecido como o próximo passo natural de segurança: protegeria contra padrões comuns de ataque (SQL injection, XSS, bots automatizados fazendo pedidos falsos) antes que o tráfego sequer alcance a instância EC2. Fica registrado no roadmap de evolução da arquitetura, junto com a introdução de um Load Balancer para alta disponibilidade multi-AZ.

## 6. Otimização de custos (FinOps)

Como a CloudAWSPizza é uma empresa de porte pequeno/médio em transição, o controle de custo é tratado como requisito de arquitetura, não como reboque:

- **AWS Free Tier**: toda a infraestrutura proposta foi dimensionada para caber dentro dos limites do Free Tier — instância EC2 `t3.micro`, RDS `db.t3.micro`, uso moderado de S3 e invocações Lambda — permitindo validar a arquitetura completa com custo próximo de zero durante o período de testes.
- **Instâncias dimensionadas para o estágio atual (não superdimensionadas)**: `t3.micro` para EC2 e `db.t3.micro` para RDS refletem a carga real esperada de uma pizzaria de porte pequeno/médio, evitando pagar por capacidade que não será usada — o rightsizing pode (e deve) ser revisado conforme o volume de pedidos cresça.
- **Desligar recursos fora de uso**: em ambientes de desenvolvimento/teste (como o Learner Lab), a prática recomendada é rodar `terraform destroy` ao final de cada sessão de testes, evitando cobrança por recursos ociosos fora do Free Tier — comportamento já registrado nas instruções operacionais da Fase 4.
- **Tagging para cost allocation**: todos os recursos (EC2, RDS, S3, Lambda) devem ser tagueados consistentemente (ex.: `project=cloudawspizza`, `environment=dev`, `owner=squad-pedidos`), permitindo que custos sejam futuramente atribuídos por squad ou por componente — pré-requisito para qualquer prática de FinOps mais madura conforme o projeto crescer.
- **Serverless onde a carga é esporádica**: a escolha de Lambda para notificações (em vez de um servidor dedicado sempre ligado) é, em si, uma decisão de custo — paga-se apenas pelas invocações reais, alinhado ao padrão de "um pedido, uma notificação".

## 7. Alinhamento com o AWS Well-Architected Framework

A arquitetura proposta é avaliada explicitamente contra os cinco pilares do Well-Architected Framework:

### Operational Excellence (Excelência Operacional)

A infraestrutura é definida como código (Terraform, Fase 4), tornando o ambiente reproduzível, versionado e auditável — eliminando a configuração manual e o conhecimento tácito identificados como problema na Fase 1. O CloudWatch fornece visibilidade operacional contínua sobre a instância EC2, substituindo o monitoramento reativo por alarmes proativos.

### Security (Segurança)

Defesa em profundidade: rede segmentada em sub-redes públicas/privadas, Security Groups restritivos por camada (app só expõe 80/443/22 restrito; banco só aceita tráfego do SG da aplicação), criptografia em trânsito e em repouso, e um caminho claro de evolução (WAF) já mapeado. A ressalva sobre o uso do `LabRole` no ambiente acadêmico está documentada de forma explícita (seção 5.1) para não mascarar o que seria a prática correta em produção.

### Reliability (Confiabilidade)

O RDS gerenciado remove uma classe inteira de falhas operacionais (backup esquecido, patch não aplicado) que existiam no modelo self-hosted. A separação entre sub-rede pública e privada limita o raio de impacto de uma eventual falha de segurança na camada de aplicação. Este pilar também é o ponto de conexão direto com a Fase 3: a proposta de arquitetura em nuvem por si só não resolve o acoplamento síncrono pagamento→pedido identificado no diagnóstico — é a evolução da aplicação para microsserviços assíncronos que efetivamente isola essa falha, e esta arquitetura AWS é o ambiente que viabiliza rodar os dois serviços de forma independente.

### Performance Efficiency (Eficiência de Performance)

Cada componente usa o modelo de serviço adequado ao seu padrão de carga (IaaS para a aplicação com carga constante, FaaS para notificações event-driven e esporádicas), evitando tanto o desperdício de capacidade ociosa quanto o gargalo de subdimensionamento. A arquitetura está pronta para introduzir um Load Balancer e escalonamento horizontal da EC2 conforme o volume de pedidos justificar.

### Cost Optimization (Otimização de Custos)

Dimensionamento dentro do Free Tier, tagging para cost allocation e uso de serverless onde a carga é esporádica (seção 6) mantêm o custo previsível e proporcional ao estágio real do negócio, sem comprometer a capacidade de evoluir a arquitetura conforme a CloudAWSPizza cresce.
