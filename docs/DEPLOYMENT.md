# Publicar o TigrIFES no GitHub Pages

O site estático usa JavaScript no navegador para os giros. Os cinco experimentos, gráficos e downloads são gerados em Python antes da publicação.

## 1. Enviar o projeto ao GitHub

Envie o código para a branch `main` do repositório `TigrIFES`, usando seu editor ou commit/push dos arquivos revisados. A pasta `site/` é gerada e fica fora do Git. O ambiente virtual, os caches e os resultados locais também são ignorados.

No GitHub Free, use repositório público para disponibilizar Pages. [Disponibilidade do recurso](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site).

## 2. Ativar a publicação

1. No repositório, abra **Settings → Pages**.
2. Em **Build and deployment → Source**, escolha **GitHub Actions**.
3. Abra **Actions → Testar e publicar no GitHub Pages**.
4. Se o push inicial ocorreu antes de ativar o Pages, use **Run workflow**, selecionando `main`.
5. Aguarde os jobs **build** e **deploy** ficarem verdes.

O arquivo `.github/workflows/pages.yml` instala dependências, executa os testes Python/JavaScript, gera `site/` e publica os arquivos estáticos. Pull requests são testados, mas não publicados. A URL aparece no resultado do deploy e em **Settings → Pages**.

**Use GitHub Actions como Source.** A opção `Deploy from a branch → /docs` não corresponde à estrutura atual: `docs/` guarda os guias; as páginas são construídas em `site/`.

Se a branch principal tiver outro nome, ajuste `branches: [main]` e as condições `refs/heads/main`. Se o ambiente `github-pages` pedir autorização de implantação, aprove na interface do GitHub.

Referência: [workflows próprios com Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## 3. Testar a URL padrão

```text
https://SEU-USUARIO.github.io/TigrIFES/
```

Confira giro, saldo após recarregar, nova sessão, escolha de semente, página de experimentos e download do ZIP.

Os links relativos atendem esse caminho e a raiz de um domínio próprio. A página 404 usa o caminho público da instalação para resolver estilos, ícone, navegação e licença em qualquer URL inexistente. O workflow obtém esse caminho automaticamente de `actions/configure-pages`. Depois de alterar o domínio próprio no GitHub, execute novamente o workflow para atualizar a página 404.

A sessão é local à origem e ao caminho da instalação: ao mudar de `github.io` para o domínio próprio, o histórico anterior não é transferido. Se o navegador bloquear armazenamento, o jogo funciona em memória e informa essa condição.

## 4. Cadastrar o domínio no GitHub

Escolha `seudominio.tech` ou um subdomínio como `tigrifes.seudominio.tech`.

Em **Settings → Pages → Custom domain**, informe o endereço sem protocolo nem caminho e salve **antes de alterar o DNS**. Como o projeto usa GitHub Actions, não é necessário adicionar arquivo `CNAME` ao código.

Referência: [domínios próprios no Pages](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site).

## 5. Configurar a get.tech / Orderbox

Com nameservers da Orderbox, como `earth.orderbox-dns.com`, selecione seu domínio na get.tech e abra **DNS Service → Manage DNS**. Se você usar nameservers de outro provedor, configure os registros no provedor responsável pelo DNS.

Para usar `seudominio.tech`, em **A Records → Add A Record** adicione:

| Host Name | Destination IPv4 Address |
|---|---|
| vazio | `185.199.108.153` |
| vazio | `185.199.109.153` |
| vazio | `185.199.110.153` |
| vazio | `185.199.111.153` |

O manual desse painel usa **Host Name vazio** para representar o domínio principal. Se a interface mostrar `@`, use o equivalente ao domínio principal. Mantenha o TTL padrão.

Para também usar `www.seudominio.tech`, em **CNAME Records → Add CNAME Record** adicione:

| Host Name | Value / Destination |
|---|---|
| `www` | `SEU-USUARIO.github.io` |

O destino não inclui `https://` nem `/TigrIFES`. Se o painel exigir nome totalmente qualificado, use `SEU-USUARIO.github.io.` com ponto final.

Para usar somente `tigrifes.seudominio.tech`, basta cadastrar esse endereço em **Custom domain** e criar este registro:

| Tipo | Host Name | Value / Destination |
|---|---|---|
| CNAME | `tigrifes` | `SEU-USUARIO.github.io` |

Nesse cenário, o domínio principal pode continuar atendendo outro site. Ajuste registros antigos conflitantes apenas do hostname escolhido e preserve os de e-mail e outros serviços. Não é necessário trocar nameservers, comprar hospedagem ou habilitar redirecionamento por frame.

Referências: [campos do painel get.tech](https://cp.get.tech/kb/servlet/KBServlet/faq471.html) e [registros DNS do Pages](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site).

## 6. Habilitar HTTPS

Depois da propagação e da validação DNS, volte a **Settings → Pages** e marque **Enforce HTTPS**. O GitHub solicita e mantém o certificado. A propagação e a disponibilização dessa opção podem levar até 24 horas.

Referência: [HTTPS no Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https).

## Atualizar e reproduzir

Cada push na `main` refaz os testes e publica uma nova versão. Os giros dos visitantes não são enviados ao repositório e não alteram os experimentos publicados.

Para conferir localmente:

```powershell
.\.venv\Scripts\python.exe -m tigrifes.build_site --output site
.\.venv\Scripts\python.exe -m http.server 8000 --directory site --bind 127.0.0.1
```

Abra `http://127.0.0.1:8000` e encerre com `Ctrl+C`. O segundo comando apenas entrega os arquivos estáticos.

## Caminho base em construções manuais

Por padrão, `python -m tigrifes.build_site` constrói para a raiz (`/`), adequada ao domínio próprio e à prévia local. Para simular a publicação no caminho do repositório:

```powershell
.\.venv\Scripts\python.exe -m tigrifes.build_site --output tmp/preview/TigrIFES --base-path /TigrIFES/
.\.venv\Scripts\python.exe -m http.server 8000 --directory tmp/preview --bind 127.0.0.1
```

Abra `http://127.0.0.1:8000/TigrIFES/`. O caminho `--base-path` é usado na página 404; as páginas normais continuam com links relativos. No GitHub Actions, esse parâmetro é preenchido automaticamente, inclusive para domínio próprio.

## Estado da validação

O site foi construído e validado localmente, incluindo testes de giro, recarga, reinício e sincronização em DOM mínimo. Não havia navegador conectado para inspeção visual real. O workflow só será executado depois de enviar o código ao GitHub. Nenhum registro DNS ou configuração da conta GitHub foi alterado nesta adaptação.

As sessões ficam no navegador, sem conta ou sincronização entre dispositivos. Os créditos são fictícios e o site não impede edição local pelo próprio visitante. Os resultados acadêmicos de referência e suas sementes estão no ZIP gerado pelo Python.

