# Arquitetura — Fase 4 (Infraestrutura)

Diagrama gerado a partir do Terraform deste diretório: um `main.tf` raiz orquestrando 7 módulos (`iam`, `vpc`, `ec2`, `rds`, `s3`, `cloudwatch`, `lambda`), provisionados na conta **AWS Academy Learner Lab** (`us-east-1`).

```mermaid
flowchart TB
    Internet["🌐 Internet"]
    Operador["🧑‍💻 Operador<br/>IP autorizado"]

    subgraph AWS["AWS Cloud · us-east-1 (AWS Academy Learner Lab)"]
        IGW["Internet Gateway"]

        subgraph VPC["VPC cloudawspizza-vpc · 10.0.0.0/16"]
            subgraph PUB["Subnet pública · 10.0.1.0/24 · us-east-1a"]
                EC2["EC2 app<br/>Amazon Linux 2023<br/>SG app-sg: 22 / 80 / 443 / 8000"]
            end
            subgraph PRIV["DB Subnet Group (subnets privadas)"]
                RDS["RDS MySQL 8.0 · db.t3.micro<br/>10.0.2.0/24 · us-east-1a<br/>SG db-sg: 3306 ← app-sg"]
                STANDBY["10.0.3.0/24 · us-east-1b<br/>(reservada, sem instância ativa)"]
            end
        end

        IAM["IAM<br/>LabRole / LabInstanceProfile"]
        CW["CloudWatch<br/>alarmes: CPU > 80%, status check"]
        LAMBDA["Lambda notify_order<br/>(sem trigger conectado)"]
        S3["S3 static bucket<br/>privado · versionado"]
    end

    Internet -->|80 / 443 / 8000| IGW
    Operador -->|22 SSH| IGW
    IGW --> EC2
    EC2 -->|3306/tcp| RDS
    IAM -. instance profile .-> EC2
    IAM -. role .-> LAMBDA
    CW -. métricas .-> EC2

    classDef network fill:#e3f3f0,stroke:#1f7d74,color:#0f4d47;
    classDef compute fill:#f7ead9,stroke:#a85a1c,color:#a85a1c;
    classDef data fill:#e4ecf8,stroke:#2f5d9e,color:#2f5d9e;
    classDef storage fill:#eaf3e2,stroke:#4a7a34,color:#4a7a34;
    classDef serverless fill:#f0e6f7,stroke:#7a4f9e,color:#7a4f9e;
    classDef observability fill:#f8e6ea,stroke:#a8455a,color:#a8455a;
    classDef security fill:#f3ecdc,stroke:#8a6a2f,color:#8a6a2f;

    class IGW,VPC,PUB,PRIV network
    class EC2 compute
    class RDS,STANDBY data
    class S3 storage
    class LAMBDA serverless
    class CW observability
    class IAM security
```

## Legenda

| Cor | Camada | Recursos |
|---|---|---|
| 🟢 Verde-água | Rede | VPC, subnets, Internet Gateway, rotas |
| 🟠 Âmbar | Computação | EC2 |
| 🔵 Azul | Dados | RDS |
| 🟩 Verde | Armazenamento | S3 |
| 🟣 Roxo | Serverless | Lambda |
| 🌸 Rosa | Observabilidade | CloudWatch |
| 🟡 Bronze | IAM / Segurança | LabRole, Security Groups |

Linha sólida = tráfego de rede permitido (SG/rota). Linha pontilhada = associação IAM ou observabilidade (sem rota de rede).

## Notas de arquitetura

- **DB Subnet Group = subnets privadas.** Não é um tipo de rede próprio: é o agrupamento lógico (`aws_db_subnet_group`) das duas subnets privadas do módulo VPC, exigido pelo RDS (mínimo 2 AZs para suportar failover), mesmo com `multi_az = false` hoje.
- **Sem NAT Gateway.** As subnets privadas não têm rota de saída à internet — o RDS não precisa de acesso externo, e isso evita o custo de um NAT Gateway (fora do escopo Free Tier deste case study).
- **IAM reaproveitado.** A conta AWS Academy bloqueia a criação de roles/policies IAM customizadas; por isso EC2 e Lambda reutilizam a `LabRole`/`LabInstanceProfile` já provisionadas, em vez do escopo mínimo recomendado em produção.
- **Lambda sem trigger.** `notify_order` está provisionada e pronta, mas nenhum evento (SNS/EventBridge/SQS) a invoca ainda — o handler documenta essa integração como próximo passo.
- **S3 desacoplado.** O bucket estático está seguro (privado, versionado), mas nenhum outro módulo o referencia no código atual.
- **Postura de demonstração.** RDS single-AZ, backup de 1 dia, `skip_final_snapshot` e `deletion_protection` desligados — adequado ao case study, não a produção.

## Módulos Terraform

| Módulo | Caminho | Provisiona |
|---|---|---|
| iam | `modules/iam` | Data sources para LabRole / LabInstanceProfile |
| vpc | `modules/vpc` | VPC, Internet Gateway, 1 subnet pública, 2 subnets privadas, route tables |
| ec2 | `modules/ec2` | Instância da aplicação, security group `app-sg` |
| rds | `modules/rds` | MySQL 8.0, subnet group, security group `db-sg`, senha aleatória |
| s3 | `modules/s3` | Bucket estático privado e versionado |
| cloudwatch | `modules/cloudwatch` | 2 alarmes de métricas na instância EC2 |
| lambda | `modules/lambda` | Função `notify_order` (Python 3.12, role `LabRole`) |
