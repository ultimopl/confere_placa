# UI (User Interface)

**Objetivo:** Fornecer a interface gráfica para o usuário, capturando interações e exibindo dados de forma intuitiva e moderna.

## Responsabilidades

* **Renderização da Interface:** Desenha a janela principal, tabelas (`Treeview`), barra de busca, painéis de histórico e diálogos de edição/adição.
* **Captura de Interação:** Monitora cliques, teclas de atalho e entradas de texto para disparar comandos ao `App`.
* **Busca em Tempo Real:** Implementa um mecanismo de *debounce* (atraso controlado) para que a busca seja disparada enquanto o usuário digita, sem sobrecarregar o sistema ou travar a interface.
* **Feedback Visual:** Atualiza cores de status (ex: verde para autorizado), mensagens de status na barra inferior e diálogos de erro/sucesso.

## Componentes Principais

* **Painel de Busca:** Campo de entrada com suporte a busca em tempo real e filtros de status.
* **Tabela Principal:** Exibição de dados com suporte a ordenação e tags de cores.
* **Painel de Histórico:** Lista de consultas recentes com possibilidade de reuso rápido.
* **Modais de Edição:** Janelas flutuantes para inserção e modificação de registros de forma isolada.

## Arquitetura

* **Dependência:** Conhece apenas o `App`, enviando eventos e recebendo dados prontos para exibição.
* **Tecnologia:** Python + Tkinter (com plano para migração para CustomTkinter).

---
