# ☁️🍕 CloudAWSPizza — Jornada de Transformação DevOps & Cloud

> De um servidor físico num datacenter local a uma arquitetura moderna, escalável e observável na AWS — cultura, arquitetura, código e infraestrutura, tudo em um único case.

## Sobre o projeto

Este repositório documenta a transformação digital completa de uma empresa fictícia, a **CloudAWSPizza**, uma pizzaria familiar que cresceu com o apoio da tecnologia mas ainda operava seu sistema de pedidos em um servidor físico local. O projeto foi desenvolvido como um case de estudo prático, unindo quatro frentes que normalmente aparecem separadas em cursos de DevOps e Cloud, mas que na vida real acontecem juntas:

1. **Cultura e processos** — como o time deveria trabalhar
2. **Arquitetura em nuvem** — onde e com que serviços construir
3. **Evolução da aplicação** — de monólito a microsserviços assíncronos
4. **Infraestrutura como código** — provisionamento real na AWS via Terraform

O objetivo não é só "usar várias tecnologias", mas mostrar o raciocínio por trás de cada decisão — por que migrar, por que quebrar o monólito, por que escolher cada serviço — como um(a) consultor(a) DevOps/Cloud faria na prática.

## O contexto (a história)

A CloudAWSPizza permite que clientes façam pedidos online e que funcionários acompanhem preparo, entrega e pagamentos. Esse sistema sempre rodou como uma aplicação única (monólito), instalada num servidor físico dentro de um pequeno datacenter local. Conforme a empresa cresceu, apareceram os problemas clássicos:

- Times de desenvolvimento e operação trabalhando isolados, sem visibilidade compartilhada
- Deploys manuais, arriscados e pouco frequentes
- Nenhuma automação de testes ou infraestrutura
- Monitoramento reativo — problemas só eram percebidos quando o cliente reclamava
- Se o módulo de pagamento travasse, o pedido inteiro travava junto (acoplamento forte do monólito)

A direção decidiu resolver isso em quatro frentes, que compõem as quatro fases deste repositório.

## Estrutura do repositório

```
cloudawspizza-transformation/
├── README.md                          ← este arquivo
│
├── 01-diagnostico-e-cultura/
│   └── plano-devops.md                ← diagnóstico, objetivos, plano de ação, governança, métricas
│
├── 02-arquitetura-cloud/
│   └── proposta-arquitetura-aws.md    ← provedor, modelos de serviço, rede, HA, segurança, custos, WAF
│
├── 03-aplicacao/
│   ├── 3a-monolito/                   ← sistema como nasceu: uma aplicação só, síncrona
│   │   └── app/
│   │       ├── main.py
│   │       ├── orders.py
│   │       └── payments.py
│   │
│   └── 3b-microservicos/              ← evolução: dois serviços independentes, comunicação assíncrona
│       ├── service-order/
│       ├── service-payment/
│       └── docker-compose.yml
│
└── 04-infraestrutura/
    ├── main.tf
    ├── variables.tf
    ├── outputs.tf
    └── modules/
        ├── vpc/
        ├── ec2/
        ├── rds/
        ├── s3/
        ├── iam/
        ├── cloudwatch/
        └── lambda/
```

## As quatro fases

### Fase 1 — Diagnóstico e cultura DevOps
📄 [`01-diagnostico-e-cultura/plano-devops.md`](./01-diagnostico-e-cultura/plano-devops.md)

Antes de tocar em qualquer tecnologia, mapeamos o cenário atual — times isolados, deploys manuais, ausência de CI/CD — e definimos objetivos mensuráveis (lead time, cobertura de testes, taxa de falhas), um plano de ação em etapas, e mudanças de governança como squads multidisciplinares e blameless post-mortems. Essa fase é o "porquê" por trás de todas as decisões técnicas que vêm a seguir.

### Fase 2 — Arquitetura em nuvem
📄 [`02-arquitetura-cloud/proposta-arquitetura-aws.md`](./02-arquitetura-cloud/proposta-arquitetura-aws.md)

Desenho da arquitetura AWS-alvo: provedor e justificativa, modelos de serviço (IaaS/PaaS/FaaS) para cada componente, estrutura de rede (VPC, sub-redes, CDN), estratégia de banco de dados, segurança (IAM, criptografia, WAF), otimização de custos (FinOps) e alinhamento com os cinco pilares do Well-Architected Framework.

### Fase 3 — Da aplicação monolítica aos microsserviços
📄 [`03-aplicacao/`](./03-aplicacao/)

**3a — Monólito:** o sistema como ele nasceu. Uma única aplicação (FastAPI), um único banco de dados, onde criar um pedido chama diretamente e de forma síncrona a lógica de pagamento — se o pagamento travar, o pedido trava junto.

**3b — Microsserviços assíncronos:** a evolução. O sistema é quebrado em `service-order` (cria e lista pedidos) e `service-payment` (processa pagamentos), comunicando-se via RabbitMQ. `service-order` publica o evento `order_created`; `service-payment` consome esse evento em background e processa o pagamento — sem nenhuma chamada HTTP direta entre os dois. Se o serviço de pagamento cair por alguns minutos, os pedidos continuam sendo aceitos normalmente.

### Fase 4 — Infraestrutura como código
📄 [`04-infraestrutura/`](./04-infraestrutura/)

Provisionamento real da arquitetura da Fase 2, adaptada ao **Free Tier da AWS**, via **Terraform**: VPC com sub-redes públicas e privadas, EC2 (t2.micro/t3.micro) hospedando a aplicação, RDS MySQL como banco de dados, S3 para arquivos estáticos, IAM com roles de menor privilégio, CloudWatch monitorando a instância, e uma função Lambda simulando notificações de novos pedidos.

## Como as fases se conectam

```
Fase 1 (Cultura)        → define COMO o time trabalha
        ↓
Fase 2 (Arquitetura)     → define ONDE e COM O QUÊ construir
        ↓
Fase 3 (Aplicação)       → evolui O QUE roda (monólito → microsserviços)
        ↓
Fase 4 (Infraestrutura)  → provisiona ONDE tudo isso roda de fato
        ↓
   (retroalimenta a Fase 1: métricas e monitoramento guiam a melhoria contínua)
```

## Stack tecnológica

| Camada | Tecnologia |
|---|---|
| Cultura e processos | Rituais ágeis, blameless post-mortems, squads multidisciplinares |
| Nuvem | AWS (EC2, RDS, S3, VPC, IAM, CloudWatch, Lambda) |
| Infraestrutura como código | Terraform |
| Aplicação | Python (FastAPI) |
| Comunicação assíncrona | RabbitMQ |
| Containers | Docker / Docker Compose |

## Como rodar cada parte

**Fase 3a — Monólito**
```bash
cd 03-aplicacao/3a-monolito
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Fase 3b — Microsserviços**
```bash
cd 03-aplicacao/3b-microservicos
docker compose up --build
```

**Fase 4 — Infraestrutura**
```bash
cd 04-infraestrutura
terraform init
terraform plan
terraform apply
```

> ⚠️ Sempre revise o `terraform plan` antes de aplicar, e rode `terraform destroy` ao final dos testes para evitar cobranças fora do Free Tier.

## Próximos passos / roadmap

- [ ] Pipeline de CI/CD (GitHub Actions) automatizando testes e deploy da Fase 3b na infraestrutura da Fase 4
- [ ] Dashboard no Grafana consumindo métricas do CloudWatch
- [ ] Terceiro microsserviço (`service-notification`) consumindo o evento `payment_processed`
- [ ] Testes automatizados (unitários e de integração) para os dois microsserviços

## Sobre este projeto

Case desenvolvido como parte de um percurso de estudos em DevOps e Cloud Computing (AWS), unindo os aprendizados de cultura DevOps, arquitetura em nuvem, arquitetura de software e infraestrutura como código em um único projeto de ponta a ponta.
