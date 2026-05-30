# Repository (Data Layer)

**Objetivo:** Gerenciar exclusivamente o armazenamento, leitura e integridade dos dados em arquivos CSV.

## Responsabilidades

* **Persistência de Dados:** Realiza a leitura e escrita de registros no formato CSV (usando delimitador `;`).
* **Escrita Atômica:** Implementa o padrão de salvamento seguro:
    1. Escreve os novos dados em um arquivo temporário (`.tmp`).
    2. Após a conclusão da escrita, substitui o arquivo original pelo temporário.
    3. Garante que o arquivo original nunca seja corrompido em caso de falha no processo.
* **Integridade de Dados:** Garante que os dados salvos sigam o esquema esperado (Placa, Detalhes, Status, Timestamp).
* **Tratamento de Erros de I/O:** Captura exceções de leitura/escrita (permissão negada, arquivo corrompido, disco cheio) e as converte em mensagens tratadas para o `App`.
* **Busca de Dados:** Oferece métodos de busca otimizados para filtrar registros dentro do conjunto de dados carregado.

## Principais Métodos

* `load(file_path)`: Carrega o conteúdo de um CSV para a memória.
* `save(data, file_path)`: Realiza a escrita atômica dos dados.
* `find_by_query(query, filters)`: Filtra os dados na memória de forma eficiente.
* `get_all()`: Retorna a lista completa de registros válidos.

---
