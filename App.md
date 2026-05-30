# App (Controller)

**Objetivo:** Atuar como o orquestrador central da aplicação, gerenciando a comunicação entre a Interface de Usuário (`UI`) e a camada de persistência (`Repository`).

## Responsabilidades

* **Orquestração de Fluxo:** Recebe eventos da `UI` (como cliques de botões ou entradas de texto) e decide qual ação o `Repository` deve tomar.
* **Gestão de Lógica de Negócio:** Valida dados antes de enviá-los para persistência e processa os resultados retornados pelo `Repository` para que a `UI` possa exibi-los.
* **Tratamento de Erros:** Captura exceções lançadas pelo `Repository` e as encaminha para a `UI` para que o usuário receba feedbacks amigáveis.
* **Desacoplamento:** Garante que a `UI` não tenha conhecimento de como os dados são salvos (CSV) e que o `Repository` não tenha conhecimento de como os dados são exibidos.

## Principais Métodos

* `process_search(query, filters)`: Recebe o termo de busca e os filtros da `UI`, solicita a busca ao `Repository` e envia os resultados de volta para a `UI`.
* `add_record(data)`: Valida os dados da placa, solicita o salvamento ao `Repository` e atualiza a `UI`.
* `delete_record(plate_id)`: Coordena o pedido de exclusão ao `Repository` e atualiza a visualização.
* `load_data(file_path)`: Gerencia a carga de um novo arquivo CSV através do `Repository`.

---
