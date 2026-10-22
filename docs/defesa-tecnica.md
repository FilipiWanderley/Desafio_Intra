# Defesa técnica — 20 minutos + 10 de perguntas

## Objetivo da apresentação

Demonstrar que o sistema **não alucina números**, preserva evidências com páginas, distingue conceito financeiro e sinaliza conflitos. Use o terminal, os três PDFs, o JSON da Light, os casos `NOT_FOUND` de Brasal/Millet e o relatório HTML. Dê preferência a decisões reais em vez de fingir que o protótipo cobre milhões de PDFs.

## Plano de 20 minutos

**0:00–2:00 — Contexto, risco e abordagem.** A Intra precisa de relatórios auditáveis; LLM sozinho não é calculadora nem auditor. Os três documentos são de 2022, não 3T25; cada um tem paginação/layout distinto. Objetivo: resultado estruturado, citável, honesto quando não há dado.

**2:00–5:00 — Arquitetura.** Mostre o diagrama do README e a separação `domain`, `application`, `infrastructure`. Explicite: ingestão preserva fonte; extrator entrega Pydantic; analisador qualitativo trabalha com evidências; validador Python detecta divergências; consolidação gera perguntas e relatório. LangGraph é dependência opcional da mesma cadeia; instale `.[agentic]` para executar no grafo.

**5:00–8:00 — Extração com evidência.** Abra `light.json`. Aponte receita em p. 9, EBITDA CVM em p. 9, dívida em p. 10 e caixa operacional em p. 25. Explique a normalização de mil para milhão e o campo `definition`. Abra `millet.json`: lucro consolidado de R$ 18,891 mi, diferente do atribuível à controladora de R$ 14,743 mi.

**8:00–11:00 — Guardrails e bugs documentais.** Abra `validation.json` e `report.md`. Mostre `SOURCE_CONFLICT` na alavancagem Light: o texto menciona 2021 duas vezes ao comparar 3,32x/3,48x. A solução mantém `conflict` e não corrige. Mostre EBITDA `not_found` em Brasal/Millet e explique por que não foi reconstruído como se estivesse no PDF.

**11:00–14:00 — Perguntas e relatório.** Abra `questions.json` e `report.html`. Explique que quatro respostas podem ter fonte incompleta, e o ranking de margem EBITDA não é seguro sem margens comparáveis. Diferencie métricas de comentários de gestão e notas: DRE comprova variação, mas não é evidência de causa.

**14:00–16:00 — Testes e evals.** Rode `python -m pytest -q` e `python -m intra_financial_ai evaluate outputs/run_ID`. Explique acurácia de número/status e página no golden set: avalia estes PDFs, não generalização. Mostre que o validador detecta variação percentual incoerente.

**16:00–18:00 — Segurança, custo e trade-offs.** PDFs são fonte não confiável. Credenciais via ambiente; conteúdo não pode executar ações; citações são conferidas. Tempo por arquivo e por etapa em `metrics.json`. Custo de LLM só é calculado quando houver tokens reais e tarifa configurada. Não inventar custo de Azure.

**18:00–20:00 — Produção Azure.** Blob + fila + workers idempotentes; Azure AI Document Intelligence para layout/OCR; AI Search para retrieval híbrido; Azure OpenAI/AI Foundry para modelos; LangGraph com checkpoint e avaliação; App Insights e Key Vault; governança e aprovação humana para conflitos. Final: foco em confiabilidade antes de automação agressiva.

## Perguntas que podem fazer

**Por que LangGraph e não CrewAI?** Porque etapas controladas, transições tipadas, rastreabilidade e possibilidade de retomar execução são mais importantes aqui do que negociação livre entre agentes. A interface do workflow permite fallback quando a dependência não está disponível.

**Por que não mandar o PDF inteiro para GPT?** Ruído, custo de contexto, dificuldades com células financeiras e citações instáveis. Primeiro normalizo a fonte e recupero evidências delimitadas.

**Vocês usam agente de verdade?** O caminho de IA é opcional e especializado na análise qualitativa; a cadeia orquestrada pode ser compilada pelo LangGraph. O core quantitativo é determinístico neste conjunto. Não denominar a execução offline como inferência por LLM.

**Por que EBITDA de Brasal e Millet não foi calculado?** O enunciado proíbe estimar informações ausentes. Um EBITDA derivado exigiria convenção e reconciliação de itens contábeis. O campo está marcado `not_found` para impedir falsa comparabilidade.

**A maior margem EBITDA é de quem?** Não é defensável comparar as três margens com o material disponível sem derivação não solicitada. O sistema abstém e oferece as evidências disponíveis.

**A Light está acima de 3x de alavancagem?** A página 10 traz dois números de covenant, mas com referências temporais ambíguas a 2021. EBITDA CVM e EBITDA ajustado para covenants não são intercambiáveis. O sistema sinaliza o conflito; não associa 3,32x a 2022 sem confirmação.

**Como validar página/trecho?** `verified` confere documento, intervalo de páginas e normalização do trecho de evidência no texto da página. A validação não depende do julgamento de outro LLM.

**Por que regex?** Pequeno conjunto documental, prazo curto e estrutura financeira previsível. É um baseline auditável barato. Limite: PDFs não padronizados exigiriam OCR/layout classification e LLM com extração estruturada sob as mesmas invariantes de evidência.

**Qual a latência/custo?** Mostrar os `metrics.json` reais; LLM desligado na demo registra zero tokens. Não alegar latência ou custo de APIs não executadas. Em produção, registrar preço por modelo e tokens reais.

**Como impedir prompt injection?** Separação forte entre system instructions e texto da fonte, modelos tipados, validação de citação, ausência de ferramentas externas abertas ao texto do PDF e credenciais fora do repositório. Para corpora externos, adicionar sandbox e política de acesso a documentos.

**Por que não MCP agora?** Não era requisito obrigatório. Depois da evidência confiável, MCP pode expor `get_metrics`, `list_documents`, `get_evidence`, `compare_companies` sem permitir que agentes alterem fatos.

**O que faria com milhares de documentos?** Jobs assíncronos escaláveis, classificação do formato, parsers/LLM por estratégia, índices híbridos com autorização, persistência de estado, deduplicação por hash, retries/DLQ, supervisão de alertas, monitoramento de custo/latência/acurácia e human review.

## Roteiro de demonstração sem improviso

```powershell
python -m pytest -q
python -m intra_financial_ai analyze data/input --output outputs
python -m intra_financial_ai evaluate outputs/run_ID --golden evals/golden_dataset.json
```

Depois, abra `report.html` no navegador; mostre `light.json`, `millet.json`, `validation.json`, `questions.json`, `metrics.json`. Faça a demo sobre uma execução já gerada se a rede estiver indisponível.

## Frases para defender as decisões

- “O meu contrato de saída não é só um número; é um número mais unidade, período, escopo e evidência.”
- “Não vou deixar o modelo escolher entre duas referências temporais conflitantes.”
- “O validador é determinístico; outro LLM não serve como auditor de matemática.”
- “Extração e geração de narrativa são responsabilidades distintas. O relatório não altera dados.”
- “Preferi entregar um núcleo verificável a afirmar que tenho RAG e multiagentes sem governança.”
