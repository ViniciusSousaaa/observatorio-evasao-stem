# Segurança das informações

A regra que seguimos no projeto é simples: nenhuma senha, chave ou token fica no repositório. Tudo que é sensível fica só na máquina de quem roda o projeto.

## O que fica fora do Git

O `.gitignore` bloqueia estes arquivos:

- `.env`: guarda a senha do banco usada na carga.
- `terraform.tfvars`: guarda o ID do projeto no Google Cloud.
- `terraform.tfstate`: arquivo que o Terraform cria para registrar o que foi criado na nuvem. Ele guarda informações sensíveis em texto puro, por isso nunca é enviado.
- Pasta `.terraform/` e o arquivo de plano `tfplan`.
- Arquivos de chave e credencial (`.pem`, `.key`, `credentials.json` e parecidos).
- A pasta `data/`, com as bases do INEP, por causa do tamanho.

No repositório ficam só os modelos `.env.example` e `terraform.tfvars.example`, que mostram quais informações são necessárias, mas sem os valores.

## Senha do banco

A senha é gerada na hora com o `openssl` e fica guardada só no `.env` local. Ela chega ao Terraform pela variável de ambiente `TF_VAR_db_password`.

No Terraform, a variável `db_password` está marcada como `sensitive`. Com isso, ela não aparece na tela durante o `plan` e o `apply`. Também colocamos uma validação que exige pelo menos 12 caracteres.

O banco é acessado por um usuário próprio do projeto (`etl_user`). A senha do usuário administrador `postgres` nunca é definida nem usada.

## Acesso ao Google Cloud

Não usamos arquivo de chave de conta de serviço. O login é feito com `gcloud auth application-default login`, que usa a conta Google da pessoa. As credenciais ficam na pasta do `gcloud` no computador, fora do projeto.

## Acesso ao banco

- A instância não libera nenhum endereço de rede. A variável `authorized_networks` começa vazia, e o Terraform recusa a liberação `0.0.0.0/0`, que abriria o banco para qualquer pessoa.
- A conexão é feita pelo Cloud SQL Auth Proxy, que confere a conta Google e cria um túnel criptografado entre o computador e o banco.
- A instância só aceita conexões criptografadas (`ssl_mode = ENCRYPTED_ONLY`).
- Os logs de conexão e desconexão estão ligados, então fica registrado quem acessou o banco.

## Backup

O Cloud SQL faz backup diário, e são mantidas as três últimas cópias. A proteção contra exclusão foi deixada desligada neste ambiente (`deletion_protection = false`) para podermos remover tudo com `terraform destroy` ao fim da disciplina e não gerar custo.
