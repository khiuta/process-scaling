# Simulador de Escalonamento de Processos — Decisões de Implementação

## 1. Visão geral

O simulador é dividido em três módulos com responsabilidades separadas:

- **`scaling.py`** — implementa oito algoritmos de escalonamento. Cada
  função roda a simulação segundo a segundo (tempo forçado com sleep) e não depende de nada relativo à
  interface visual.
- **`visuals.py`** — consome os eventos gerados por `scaling.py` (via o
  parâmetro `on_tick`) e desenha um painel Gantt ao vivo por algoritmo,
  usando matplotlib.
- **`main.py`** — ponto de entrada: lê o arquivo de configuração
  (quantum/aging), lê os processos (stdin ou CSV), pergunta quais algoritmos
  rodar e inicia o painel.

## 2. Estrutura de dados para controle de processo

Cada processo de entrada vira um dicionário simples com os dados estáticos:

```python
{'task': 1, 'start_time': 0, 'duration': 5, 'priority': 2}
```

Durante a simulação, cada processo ganha um segundo dicionário — o "task-info"
— que envolve o processo estático e guarda o estado mutável de controle:

```python
{
    'task': <dict acima>,        # dados estáticos do processo
    'wait_time': 0,               # segundos acumulados esperando na fila
    'executed_time': 0,           # segundos já executados (burst decorrido)
    # campos presentes apenas nos algoritmos que precisam deles:
    'quantum': 2,                 # RR: quantum restante da fatia atual
    'dynamic_priority': 5,        # priod / RR_prio_aging: prioridade após envelhecimento
    'quantum_left': 1,            # RR_prio_aging: quantum restante
    'finish_time': 14,            # preenchido quando o processo termina
}
```

Essa escolha mais simples foi preferida do que criar uma classe por ser mais 
flexível com atributos e mais fácil de printar.

`status` explícito não é armazenado, é apenas implícito checando dados da task e task-info

| Situação                       | task-info                                        |
|--------------------------------|--------------------------------------------------|
| Pronto / esperando             | lista/deque `waiting` (ou `queue`)                |
| Executando                     | variável `curr_proc`                              |
| Terminado                      | lista `finished_procs`                            |

Isso evita novo campo `status`.

## 3. Fila de espera

A fila de processos em espera é uma lista Python simples, e a
escolha de quem roda a seguir é feita por uma função de escolha,
`_select_next`, chamada sempre que uma decisão de escalonamento precisa ser tomada.

```python
def _select_next(candidates, metric_func, running=None):
    # 1) melhor valor de metric_func entre os candidatos
    # 2) empate? prefere `running` (processo que já está com a CPU)
    # 3) empate ainda? prefere o de menor tempo restante (SRT)
    # 4) empate ainda? aleatório
```

`metric_func` é o critério de cada algoritmo (duração para SJF, prioridade
negativa para os algoritmos de prioridade, tempo restante para SRTF). Essa
função única é reaproveitada por SJF, SRTF, prioridade cooperativa,
prioridade preemptiva, prioridade com envelhecimento e round-robin com
prioridade e envelhecimento — garantindo que todos sigam exatamente a mesma
política de desempate em vez de cada um reimplementá-la.

No caso de FCFS e Round Robin que não tem critério para desempatar,
os processos que chegam ao mesmo tempo são ordenados e empates são
resolvidos aleatoriamente.

## 4. Os oito algoritmos

| # | Algoritmo | Preempção | Observações de implementação |
|---|-----------|-----------|-------------------------------|
| 1 | FCFS | Não | Fila FIFO simples (`deque`). |
| 2 | Round Robin | Por quantum | Fila FIFO; processo volta ao fim da fila quando o quantum expira. |
| 3 | SJF | Não | `_select_next` por duração. |
| 4 | SRTF | Sim (a cada segundo) | `_select_next` por tempo restante, reavaliado todo tick. |
| 5 | Prioridade cooperativa | Não | `_select_next` por prioridade estática. |
| 6 | Prioridade preemptiva | Sim (a cada segundo) | `_select_next` por prioridade estática, reavaliado todo tick. |
| 7 | Prioridade com envelhecimento | Sim (a cada segundo) | Como (6), mas a prioridade dinâmica de quem espera sobe 1×/segundo. |
| 8 | Round Robin + prioridade + envelhecimento | Só por quantum | Ver seção 4.1. |

### 4.1 Round Robin + prioridade + envelhecimento (algoritmo 8)

Um detalhe: quando o quantum de um processo expira mas ele continua
sendo o de maior prioridade dinâmica entre os candidatos, ele é escolhido de
novo pela própria regra 1 de desempate — mesmo sem ter havido de fato uma
"troca" de processo em execução. Isso é detectado corretamente pelo contador
de trocas de contexto (que só incrementa quando o processo que roda em um
segundo é *diferente* do que rodou no segundo anterior), então esse caso não
conta como troca de contexto.

## 5. Métricas de saída

Ao final de cada algoritmo, o programa imprime em stdout:

- **Tempo médio de espera** (*mean wait time*): média de `wait_time` sobre
  os processos terminados.
- **Tempo médio de vida** (*turnaround time*): `wait_time + duration` de
  cada processo.
- **Número de trocas de contexto**: contado comparando, segundo a segundo,
  se o processo em execução mudou de identidade em relação ao segundo
  anterior (com exceção da primeira execução).

## 6. Entrada

Dois formatos são aceitos:

- **CSV** (`--csv caminho.csv`), formato original do arquivo:
  `task,start_time,duration,priority` — um processo por linha, id (task)
  explícito.
- **stdin** (padrão, quando `--csv` não é passado), formato do enunciado:
  `instante_criação duração prioridade`, um processo por linha, campos
  separados por um ou mais espaços. O id da tarefa não vem na entrada, é
  o número da linha (1-indexed).

## 7. Configuração (quantum / aging)

Lida de um arquivo texto simples via `--config caminho`:

```
quantum:2
aging:1
```

Espaços ao redor do `:` são tolerados. Qualquer uma das duas chaves ausente
do arquivo (ou a ausência total de `--config`) cai para um valor padrão
(`quantum=2`, `aging=1`), então o programa nunca falha por causa de uma
configuração incompleta.

## 8. Seleção de algoritmos e por que existe `--algorithms`

Como os processos agora podem vir da entrada padrão (stdin), não é possível
também usar stdin para perguntar interativamente quais algoritmos rodar —
no momento em que o programa terminar de ler os processos, o stdin 
já estará no fim do arquivo. Por isso:

- Se `--algorithms 1,3,5,7` for passado, essa lista é usada diretamente
  (necessário sempre que os processos vierem de stdin).
- Se não for passado e o stdin for um terminal de verdade (ou seja, os
  processos vieram de `--csv`, então stdin está livre), o programa volta ao
  menu interativo original.

## 9. Interface visual

`visuals.py` roda cada algoritmo escolhido em uma thread separada (até 4
simultâneas), cada uma empurrando eventos por segundo numa fila
thread-safe. A thread principal (dona da janela matplotlib) drena essas
filas e redesenha um Gantt horizontal por algoritmo, com:

- cor sólida = executando, branco = esperando, barra congela no instante
  em que o processo termina
- crescimento suave da barra atual
- prioridade/prioridade dinâmica no rótulo do eixo Y, quando aplicável
- tempo médio de espera exibido por painel
- layout 1/2/3/4 painéis ajustado automaticamente (`subplot_mosaic`).

Esse módulo não é lido nem importado por `scaling.py` — o acoplamento é
unidirecional, então `scaling.py` continua funcionando (e sendo testável)
sem matplotlib instalado.
