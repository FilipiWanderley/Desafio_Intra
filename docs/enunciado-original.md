# Teste Prático — Engenheiro(a) de IA · Intra

## Análise Inteligente de Demonstrações Financeiras

---

## Contexto

Os analistas financeiros da Intra leem todo trimestre dezenas de **releases de resultados, comentários de desempenho e notas explicativas** de empresas. É um trabalho manual, lento e sujeito a erro.

Queremos uma solução de IA que **leia esses documentos, extraia as informações relevantes de forma confiável e entregue um relatório pronto para o analista**.

## Material fornecido

Você vai receber **3 documentos em PDF** de empresas de capital aberto: releases de resultados ou demonstrações financeiras trimestrais com comentário da administração. Os documentos têm formatos e estruturas diferentes de propósito.

## Prazo e entrega

- **Prazo:** 3 dias corridos a partir do recebimento.
- **Esforço estimado:** de 6 a 8 horas. Não esperamos uma solução completa de produção. Esperamos **boas decisões, bem explicadas**.
- **Entrega:** um repositório Git (GitHub, GitLab ou Azure DevOps), com acesso liberado para o avaliador.
- **Apresentação:** 20 minutos explicando a solução, mais 10 minutos de perguntas.

---

## O que a solução deve fazer

### 1. Ingestão do documento
Ler os PDFs e extrair **texto e tabelas**. Use a ferramenta que preferir: Azure AI Document Intelligence, bibliotecas open source, um LLM multimodal etc.

### 2. Extração estruturada
Para **cada documento**, gere um JSON com pelo menos os campos abaixo:

| Campo | Exemplo |
|---|---|
| Empresa e período de referência | "Empresa X", "3T25" |
| Receita líquida | valor, unidade, variação contra o período comparável |
| EBITDA (ou EBITDA ajustado) e margem | valor, %, variação |
| Lucro líquido | valor, variação |
| Dívida líquida e alavancagem (Dívida líquida / EBITDA) | valor, múltiplo |
| Fluxo de caixa operacional ou Capex | se disponível |

**Cada valor extraído precisa informar a origem:** página e trecho do documento onde foi encontrado.

Quando uma informação **não existir** no documento, o campo deve vir explicitamente como **não encontrado**. Não pode ser estimado nem inventado.

### 3. Análise qualitativa do comentário da administração
Para cada documento, identifique:
- os **principais motivos** do resultado no período (o que explicou a melhora ou a piora);
- os **riscos e pontos de atenção** citados;
- o **guidance** ou as perspectivas, se houver;
- **eventos relevantes**, como aquisições, reestruturações, contingências ou mudanças contábeis;
- o **tom geral** da administração (positivo, neutro ou negativo), **com a justificativa**.

### 4. Perguntas em linguagem natural
A solução deve responder perguntas livres sobre os documentos. Rode e entregue as respostas para estas 5 perguntas:

1. Qual empresa teve a maior margem EBITDA no período?
2. O que a administração de cada empresa apontou como principal motivo da variação da receita?
3. Alguma das empresas está com alavancagem acima de 3x? Qual?
4. Quais riscos são citados por mais de uma empresa?
5. Qual é o guidance de cada empresa para o próximo ano?

Toda resposta deve **citar a fonte**: documento e página.

### 5. Validação e consistência
Implemente **verificações automáticas** sobre o que foi extraído. Por exemplo:
- a margem calculada (EBITDA dividido pela receita) bate com a margem informada?
- as variações percentuais batem com os valores dos dois períodos?
- as unidades estão consistentes (mil, milhões, bilhões)?

Inconsistências devem aparecer **sinalizadas no relatório**, não corrigidas em silêncio.

### 6. Relatório final
Gere um **relatório consolidado** em Markdown, HTML ou PDF, para um analista financeiro, contendo:
- um resumo executivo, com até 5 linhas por empresa;
- uma tabela comparativa dos indicadores das 3 empresas;
- a análise qualitativa;
- as respostas às 5 perguntas;
- os alertas de inconsistência e de informações não encontradas.

---

## Explicação da solução (README e apresentação)

No README e na apresentação, explique:

1. **Arquitetura:** o fluxo de ponta a ponta, de preferência com um diagrama.
2. **Decisões e trade-offs:** por que escolheu cada ferramenta, modelo e abordagem (extração, chunking, prompts, orquestração).
3. **Combate à alucinação:** como você garante que os números estão corretos e vieram do documento.
4. **Avaliação de qualidade:** como você mediu se a extração está certa, e com que resultado.
5. **Custo e desempenho:** custo estimado em tokens e em dinheiro e o tempo de processamento por documento.
6. **Segurança:** como você trata credenciais e conteúdo malicioso dentro dos documentos.
7. **Limitações:** o que não funciona bem hoje.
8. **Caminho para produção:** o que mudaria para processar milhares de documentos por trimestre no **Azure**. Pense em AI Foundry, Document Intelligence, AI Search, observabilidade e custo.

---

## Regras

- **Linguagem:** Python, de preferência.
- **Modelo e provedor de LLM:** livre (Azure OpenAI, OpenAI, Claude, modelos open source etc.).
- **Credenciais:** ⚠️ **nunca** deixe chaves de API no repositório. Entregue um `.env.example`.
- **Execução:** o README deve permitir rodar a solução com poucos comandos.
- **Ferramentas de IA:** você pode usar assistentes de código, como Copilot ou Claude Code. Na apresentação, vamos perguntar sobre qualquer parte do código.

## Diferenciais (opcionais)

- Orquestração com **agentes**, por exemplo um agente extrator, um validador e um redator do relatório.
- Um **servidor MCP** que exponha os dados extraídos para outros agentes.
- Um **conjunto de avaliação** automatizado, com valores esperados e métricas de acerto.
- Uso de **ML tradicional** onde fizer sentido, por exemplo classificar o tom ou detectar anomalias, comparando com a abordagem por LLM.
- Docker, testes automatizados e logs ou traces de execução.

---

**Dúvidas:** envie para o recrutador. Se algo não estiver claro, **registre a premissa que você adotou no README** e siga em frente. Isso também faz parte da avaliação.
