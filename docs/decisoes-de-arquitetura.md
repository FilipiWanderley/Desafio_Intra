# Registro de decisões — Intra Financial AI

## ADR-01 · Evidência antes de resposta

**Decisão:** Toda métrica e observação qualitativa terá origem documentada antes de ser consolidada. Página corresponde à página física do PDF. O trecho é verificável pelo validador.

**Motivo:** LLM responde fluentemente mesmo sem dado; bancos precisam demonstrar proveniência.

**Trade-off:** Citabilidade aumenta tamanho do resultado, mas permite auditoria humana.

## ADR-02 · Math in Python

**Decisão:** Variações, tolerâncias, status e consistência de unidade são operações determinísticas. LLM é enriquecimento sem autoridade para corrigir dados.

**Motivo:** Diferenças de unidade e valor podem alterar análise financeira em ordens de magnitude.

**Trade-off:** Necessita parser/contrato explícito em vez de pedir uma resposta livre.

## ADR-03 · Abstinência explícita

**Decisão:** Dado ausente retorna `not_found`, divergência retorna `conflict`, valor não é estimado para preencher buraco.

**Motivo:** O próprio enunciado exige ausência explícita.

**Trade-off:** Algumas perguntas ficam parcialmente respondidas; isso é melhor do que falsa precisão.

## ADR-04 · LangGraph opcional e reprodução local

**Decisão:** Mesmo workflow é executável por StateGraph, quando a dependência está instalada, ou por sequência determinística quando offline. Manifesto declara o motor usado.

**Motivo:** Reprodutibilidade da análise é mais importante que dependência de rede.

**Trade-off:** A versão não implementa persistência de checkpoints e fila de retries de produção.

## ADR-05 · Não misturar escopos contábeis

**Decisão:** Preferência por coluna consolidado, controle da unidade e anotação de definições de EBITDA/CVM/covenants. Resultado da controladora e consolidado não devem ser misturados.

**Motivo:** Fontes reais têm múltiplas colunas e conceitos, por exemplo a demonstração Millet.

**Trade-off:** Métrica disponível em um segmento específico não é promovida automaticamente a métrica do grupo.
