> **Status:** research input, not a specification. Written 2026-11 as the starting point for
> FlowGlyph. The original citation markers did not resolve to URLs and were removed. Verified
> sources are listed at the end; claims marked *unverified* could not be confirmed and should not
> be repeated as fact.

# Arquitectura open source para traducir automatizaciones empresariales a herramientas y flujos gobernables por agentes

## Resumen ejecutivo

La idea que describes tiene sentido y, a noviembre de 2026, **no parece existir un proyecto open source consolidado que resuelva exactamente el problema completo**: ingerir automatizaciones de distintos ecosistemas empresariales, como UiPath y SAP, extraer de forma determinista su semántica operacional, normalizarlas en una representación mínima y vendor-neutral, exponerlas como herramientas para agentes, y permitir después reconstruir flujos ejecutables a partir de lenguaje natural o de un PDD/documento de requisitos.

Sí existen piezas importantes del problema. UiPath ya puede exponer workflows RPA, actividades, agentes, API workflows y procesos Maestro BPMN como herramientas MCP, y además su Autopilot puede generar procesos BPMN a partir de lenguaje natural, PDDs, mapas de procesos o documentos. SAP dispone ya de varias superficies MCP, entre ellas Automation Pilot y SAP Integration Suite, y está llevando progresivamente sus APIs y procesos hacia interfaces consumibles por agentes.

También empiezan a aparecer herramientas independientes que analizan XAML de UiPath. Por ejemplo, `xaml-parser` extrae argumentos, variables, actividades, expresiones y anotaciones, y Workflow Lens reconstruye el grafo de llamadas entre workflows para proporcionar una visión global del proceso. Existen además visualizadores capaces de reconocer centenares de actividades y representar secuencias, flowcharts y state machines.

Sin embargo, esas soluciones se concentran principalmente en **leer UiPath**, **exponer capacidades existentes por MCP** o **generar automatizaciones dentro de un producto concreto**. La oportunidad diferencial sería construir una capa intermedia abierta que trate UiPath, SAP, APIs, BPMN y futuros sistemas simplemente como distintas fuentes de una misma representación operacional.

Mi recomendación sería plantearlo no como «otro MCP server», sino como una especie de **compiler toolchain para automatizaciones empresariales**:

**UiPath / SAP / BPMN / OpenAPI → parser determinista → Automation IR → catálogo semántico → MCP/OpenAPI/A2A → compilador de workflows**

Esa separación es la que podría convertir el proyecto en algo técnicamente interesante y publicable, en lugar de quedar como otro wrapper alrededor de un LLM.

## El espacio que ya existe

### UiPath está avanzando muy rápido hacia este modelo

Conviene partir de una realidad importante. UiPath está construyendo en 2026 una parte considerable de esta visión dentro de su propia plataforma.

Su servidor MCP nativo permite seleccionar artifacts ya existentes y publicarlos como herramientas. Entre los tipos admitidos están workflows RPA, Integration Service activities, agentes, API workflows y procesos Maestro BPMN. La plataforma se ocupa de hosting, descubrimiento, autenticación y gobierno.

Además, UiPath ha introducido un conector MCP universal que permite consumir herramientas de servidores MCP desde RPA, API Workflows y Maestro. El conector alcanzó disponibilidad general en agosto de 2026 y soporta autenticación OAuth 2.0 y basada en tokens.

Más relevante todavía para tu idea es Maestro. En septiembre de 2026 UiPath documenta flujos en los que un desarrollador puede proporcionar un proceso, un BPMN existente, un mapa de proceso o un PDD y dejar que un coding agent proponga un plan, genere el workflow, lo depure y posteriormente lo despliegue.

UiPath también publica hoy una cantidad considerable de conocimiento técnico estructurado sobre sus actividades. Su repositorio `UiPath/skills` incluye documentación de activities, parámetros, configuraciones válidas, ejemplos XAML y reglas para que coding agents puedan construir automatizaciones. Hay incluso una petición abierta de la comunidad solicitando una biblioteca oficial y machine-readable de metadata de todas las activities, precisamente porque actualmente buena parte del tooling externo tiene que reconstruir esa información.

Esto es especialmente interesante porque confirma que **el problema de extraer una taxonomía machine-readable de activities es real y todavía no está perfectamente resuelto de forma pública**.

### SAP también está convergiendo hacia herramientas agent-ready

SAP ya soporta MCP en distintas capas. Automation Pilot permite seleccionar comandos y publicarlos como tools para agentes. Cada herramienta proporciona nombre, descripción, inputs y hints como `readOnly`, `destructive` e `idempotent`. Los secretos o inputs prefijados pueden ocultarse del contrato que ve el agente.

SAP Integration Suite permite además envolver APIs y Business Data Graphs como servidores MCP y publicarlos para su descubrimiento. SAP publicó un tutorial específico de esta arquitectura el 2 de noviembre de 2026.

SAP también ha lanzado infraestructura MCP para administración de BTP y existe una distribución oficial orientada a operar ABAP/BTP desde clientes compatibles con MCP, con controles por landscape y distintos niveles de acceso.

Por tanto, «hacer SAP accesible a un agente» por sí solo no constituiría una diferenciación fuerte. La diferenciación estaría en **extraer, describir y normalizar la semántica de cualquier automatización**, independientemente de si originalmente era SAP, UiPath, BPMN, una API o código.

### Hay herramientas que resuelven fragmentos del problema

En UiPath ya existe un parser open source que transforma XAML en estructuras que contienen argumentos, variables, activities y expresiones, con validación mediante JSON Schema.

Workflow Lens va un paso más allá. Resuelve `Invoke Workflow File`, reconstruye el call graph y puede generar una representación más adecuada para proporcionar contexto a agentes. Su licencia es Apache 2.0.

UiPath XAML Viewer interpreta Classic y Modern workflows y reconoce más de 200 tipos de activities en múltiples categorías, además de representar workflows secuenciales, flowcharts y state machines.

En el lado de ejecución agentic existen proyectos como OpenWOP, que propone un protocolo para workflows multiagente con schemas, OpenAPI, AsyncAPI, ejecución reproducible e idempotency keys. Temporal proporciona ejecución durable, retries y mecanismos para diseñar Activities idempotentes. Conductor OSS integra llamadas MCP como tareas de workflow.

Lo que no encontré en la investigación es una implementación madura que combine esas capas de la siguiente forma:

**reverse engineering estructural de automatizaciones + IR vendor-neutral + clasificación semántica + garantías de ejecución + generación de workflows + exposición MCP**.

Eso es, en mi opinión, el hueco más interesante.

## La arquitectura que construiría

La decisión más importante sería **no utilizar un LLM para aquello que puede determinarse estáticamente**.

Por ejemplo, un XAML de UiPath ya contiene activity types, atributos, inputs, outputs, variables, scopes, namespaces, dependencias y estructura de control. Esa información debería extraerse mediante parsing convencional. Lo mismo ocurre con OpenAPI, BPMN y buena parte de los metadatos SAP. OpenAPI está diseñado precisamente para permitir que máquinas entiendan operaciones, identificadores, parámetros, esquemas y respuestas sin inspeccionar el código de implementación. BPMN proporciona además un formato interoperable para representar procesos entre distintas herramientas.

El pipeline ideal sería:

```text
                    ┌───────────────┐
UiPath XAML ───────►│               │
SAP metadata ──────►│   ADAPTERS    │
BPMN ──────────────►│               │
OpenAPI ───────────►│               │
Custom SDK ────────►│               │
                    └───────┬───────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │  AUTOMATION IR  │
                   │                 │
                   │ capabilities    │
                   │ inputs/outputs  │
                   │ side effects    │
                   │ idempotency     │
                   │ auth/scopes     │
                   │ dependencies    │
                   │ control flow    │
                   │ failure model   │
                   └────────┬────────┘
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
       MCP server      Flow compiler    Static docs
             │              │
             ▼              ▼
          Agent        UiPath/SAP/BPMN
```

La pieza verdaderamente importante sería el **Automation IR**, no MCP.

MCP sería simplemente una de las interfaces de salida.

### Un IR mínimo

Yo diseñaría una operación aproximadamente así:

```yaml
id: sap.invoice.create
version: 1.2.0

kind: action

semantics:
  verb: create
  entity: invoice
  domain: finance

input:
  schema: schemas/create_invoice.input.json

output:
  schema: schemas/invoice.output.json

effects:
  mutates_state: true
  destructive: false
  external: true

execution:
  idempotency: conditional
  idempotency_key: invoice.external_reference
  retry: safe_with_key
  timeout: 30s

security:
  scopes:
    - invoice.write
  approval: required_above_threshold

errors:
  - DUPLICATE_REFERENCE
  - CUSTOMER_NOT_FOUND
  - VALIDATION_ERROR

source:
  provider: sap
  artifact: CreateInvoice
  artifact_version: "4.7"

adapter:
  type: sap-api
```

Ese documento debería ser suficientemente pequeño para que un planner pueda trabajar sobre miles de herramientas sin enviar su documentación completa al modelo.

MCP ya proporciona cuatro conceptos útiles para esta taxonomía: `readOnlyHint`, `destructiveHint`, `idempotentHint` y `openWorldHint`. No obstante, la propia especificación advierte que son **hints, no garantías**, y que clientes no deben asumir que son verdaderos cuando proceden de servidores no confiables.

Por ello, yo extendería internamente el modelo bastante más:

```text
read_only
mutating
destructive
idempotent
conditionally_idempotent
retryable
compensatable
transactional
long_running
human_approval_required
external_side_effect
reversible
deterministic
```

Esos atributos permiten razonar sobre workflows sin pedirle al modelo que «entienda» nuevamente cada actividad en cada ejecución.

### Idempotencia debería ser una propiedad de primera clase

Este punto es especialmente importante para sistemas empresariales.

Temporal asume que Activities pueden volver a ejecutarse debido a fallos y retries, y por ello recomienda explícitamente diseñarlas para ser idempotentes. También utiliza IDs estables para conseguir comportamiento efectivamente único ante retries en determinados escenarios.

En tu IR no utilizaría simplemente:

```yaml
idempotent: true
```

sino algo parecido a:

```yaml
idempotency:
  mode: key
  key:
    fields:
      - customer_id
      - external_reference
  scope: tenant
  ttl: 24h
```

o:

```yaml
idempotency:
  mode: none
  compensation: cancel_invoice
```

Eso haría posible que un compilador determine automáticamente dónde puede hacer retry, dónde necesita confirmación humana y dónde necesita una operación compensatoria.

### Debería existir un grafo, no solamente un catálogo de tools

Los sistemas que quieres traducir son esencialmente grafos de ejecución.

BPMN ya define tareas, gateways, eventos y flujo de control, y dispone de un formato machine-readable estandarizado.

Por tanto, modelaría dos objetos diferentes:

```text
Capability
```

Una operación elemental.

```text
Workflow
```

Un grafo que compone capabilities.

Algo como:

```yaml
workflow: invoice_processing

nodes:
  - id: read_mail
    capability: outlook.email.read

  - id: extract_invoice
    capability: document.invoice.extract

  - id: create_invoice
    capability: sap.invoice.create

edges:
  - from: read_mail
    to: extract_invoice

  - from: extract_invoice
    to: create_invoice
    condition: extraction.confidence >= 0.95
```

Esto permite que el mismo workflow se compile posteriormente a diferentes backends.

## Cómo reducir radicalmente el uso de tokens

Aquí creo que hay una oportunidad especialmente buena.

El error sería cargar en el contexto del agente todas las activities de UiPath o todas las operaciones SAP. Miles de schemas completos consumirían una enorme cantidad de contexto y además empeorarían la selección de herramientas.

El sistema debería separar **discovery**, **planning** y **execution**.

### El catálogo no debería entrar completo al LLM

Cada capability podría tener un descriptor extremadamente compacto:

```json
{
  "id":"sap.invoice.create",
  "d":"create supplier invoice",
  "in":["vendor","amount","currency","ref"],
  "out":["invoice_id"],
  "e":"W",
  "i":"KEY",
  "a":"invoice.write"
}
```

Un catálogo de diez mil operaciones seguiría siendo indexable sin proporcionar diez mil JSON Schemas completos al modelo.

Después se realizaría:

```text
Requirement
    ↓
search/retrieval
    ↓
20 candidate capabilities
    ↓
LLM planning
    ↓
5 selected capabilities
    ↓
load full schemas only for those 5
```

OpenAPI utiliza `operationId` como identificador único de operaciones precisamente para que tooling pueda referirse a ellas programáticamente. JSON Schema puede describir y validar los contratos de entrada y salida.

Por ello construiría tres niveles de representación:

```text
L0  fingerprint
     20-100 bytes

L1  semantic card
     100-400 tokens

L2  full contract
     JSON Schema + constraints + examples
```

La mayor parte del tiempo el agente solamente debería ver L0 o L1.

### El LLM debería completar semántica, no descubrir estructura

Por ejemplo, de este XAML:

```xml
<ui:Click
    DisplayName="Submit invoice"
    Selector="..." />
```

el parser puede determinar sin IA:

```text
activity_type = Click
display_name = Submit invoice
selector = ...
scope = ...
position_in_graph = ...
```

Solo entonces el modelo podría inferir:

```text
intent = submit_invoice
business_domain = accounts_payable
risk = external_state_change
```

Y esa inferencia debería almacenarse.

Nunca debería volver a pagarse ese razonamiento en cada ejecución.

La estrategia podría ser:

```text
parse once
→ enrich once
→ human review when uncertain
→ persist normalized capability
→ reuse indefinitely
```

Esto convierte el LLM en una fase de **compilación semántica**, no en el runtime completo.

### Un hash debería impedir análisis duplicados

Cada artifact fuente podría tener:

```text
source_hash
parser_version
semantic_model_version
ir_version
```

Si el hash y parser no cambian, no hay que volver a analizarlo.

Si solamente cambia la descripción humana pero no el schema operacional, puede regenerarse únicamente la capa semántica.

Con miles de actividades, esa diferencia puede reducir de forma considerable el consumo recurrente del modelo.

## Cómo permitir construir flujos hablando o desde un documento

El segundo gran componente sería un **workflow compiler**.

El usuario podría escribir:

> Cuando llegue una factura por correo, comprueba que el proveedor existe en SAP. Si el importe supera 10.000 €, solicita aprobación. Después crea la factura y archiva el PDF.

El modelo no generaría directamente XAML o ABAP.

Generaría primero una representación intermedia:

```yaml
goal: process_invoice

steps:
  - find:
      capability: email.receive

  - find:
      capability: invoice.extract

  - find:
      capability: sap.vendor.lookup

  - condition:
      expression: invoice.amount > 10000

  - find:
      capability: approval.request

  - find:
      capability: sap.invoice.create

  - find:
      capability: document.archive
```

Después el compilador resolvería cada capability contra el catálogo y produciría un workflow validable.

Esto tiene una ventaja crítica: **el modelo nunca tiene que conocer el formato propietario completo del destino**.

Puede producir un Automation IR estable, y los backends pueden generar:

```text
Automation IR
   ├──► UiPath XAML
   ├──► UiPath Maestro BPMN
   ├──► SAP Build Process Automation
   ├──► Temporal
   ├──► n8n
   ├──► BPMN
   └──► Python/TypeScript
```

UiPath ya demuestra que la generación de BPMN desde PDD o lenguaje natural es viable dentro de su ecosistema. Su producto puede recibir documentos, procesos o modelos existentes, proponer un plan y construir el proceso.

Tu proyecto sería más interesante si hiciese lo mismo **sin convertir un proveedor concreto en el lenguaje intermedio**.

## MCP, seguridad y ejecución profesional

MCP encaja muy bien como interfaz de ejecución, pero no debería ser confundido con el modelo de workflow.

La especificación MCP de julio de 2026 ha evolucionado hacia un core stateless y reforzado mecanismos de autorización y extensibilidad.

Para servidores HTTP, los SDK oficiales tratan el servidor MCP como un OAuth Resource Server. Se espera que valide bearer tokens, audience/resource y scopes. El servidor puede además exigir scopes diferentes para operaciones concretas.

Por tanto diseñaría:

```text
Agent
  │
  │ OAuth / scoped credential
  ▼
MCP Gateway
  │
  ├── policy engine
  ├── approval engine
  ├── idempotency store
  ├── audit log
  └── credential broker
        │
        ├── UiPath
        ├── SAP
        └── other systems
```

El agente **no debería recibir las credenciales finales de SAP o UiPath**.

El gateway debería poseerlas o adquirirlas mediante un identity provider y realizar la llamada en nombre del usuario o servicio.

SAP ya sigue patrones similares. Automation Pilot permite asignar permisos MCP a service accounts y restringirlos a servidores concretos.

Además, no confiaría únicamente en los hints MCP. Como indica la especificación, un servidor puede afirmar que una operación es read-only o idempotente sin que exista ninguna garantía técnica de ello.

Tu runtime debería validar esas propiedades mediante policies propias.

Por ejemplo:

```yaml
policy:
  capability: sap.payment.execute

  requires:
    role: finance_operator
    approval: true

  constraints:
    amount:
      max: 5000

  environment:
    production: true
```

El planner puede decidir **qué debería ocurrir**.

El policy engine decide **qué está autorizado a ocurrir**.

Esa separación es fundamental.

## Cómo publicaría el proyecto open source

Para un proyecto así, la licencia no debería ser una decisión secundaria.

Mi opción inicial sería **Apache License 2.0**.

Apache 2.0 está aprobada por la OSI, permite uso comercial, modificación y redistribución, e incluye una concesión explícita de derechos de patente de los contribuidores. También deja fuera de la licencia los derechos sobre marcas, lo que permite mantener separada la identidad comercial del proyecto.

Eso es especialmente útil aquí porque probablemente quieras que consultoras, integradores y empresas puedan adoptar el proyecto sin miedo a una obligación copyleft amplia.

La alternativa que consideraría seriamente sería **MPL 2.0** si quieres que las modificaciones directas sobre tu core tengan que permanecer abiertas. MPL aplica copyleft a nivel de archivo, pero permite que esos archivos formen parte de aplicaciones propietarias más grandes.

En términos prácticos:

| Objetivo | Licencia |
|---|---|
| Máxima adopción empresarial | **Apache-2.0** |
| Que mejoras al core vuelvan al proyecto | **MPL-2.0** |
| Obligar a abrir productos derivados completos | GPL/AGPL |
| Proyecto cerrado con source visible | No llamarlo open source |

Para lo que describes elegiría **Apache-2.0 + trademark policy**.

La marca comercial y el nombre pueden protegerse independientemente del código. Apache 2.0 expresamente no concede automáticamente derechos sobre marcas del licenciante.

Además pondría desde el primer commit:

```text
LICENSE
NOTICE
README.md
SECURITY.md
CONTRIBUTING.md
CODE_OF_CONDUCT.md
GOVERNANCE.md
TRADEMARKS.md
THIRD_PARTY_NOTICES.md
DCO
```

y headers SPDX:

```text
SPDX-License-Identifier: Apache-2.0
```

SPDX proporciona identificadores normalizados para licencias y está diseñado para que herramientas y organizaciones puedan intercambiar información sobre composición y licencias de software. Linux Foundation recomienda identificar tanto la licencia del proyecto como las de las dependencias externas.

Para contribuciones externas usaría inicialmente **DCO**, no un CLA complejo. El Developer Certificate of Origin permite que cada contributor certifique mediante su `Signed-off-by` que tiene derecho a aportar ese código bajo la licencia del proyecto.

### La seguridad del repositorio puede convertirse en parte del producto

Si quieres que el proyecto parezca realmente serio desde el primer día, añadiría supply-chain security desde el inicio.

OpenSSF Scorecard analiza automáticamente prácticas de seguridad de repositorios open source y puede integrarse como GitHub Action.

OpenSSF mantiene además su Best Practices Badge, con requisitos progresivos sobre seguridad, proceso de contribución, canales cifrados, testing y mantenimiento.

Los releases deberían generarse exclusivamente desde CI y firmarse.

Sigstore/Cosign permite firmar artefactos utilizando identidades OIDC y verificar posteriormente la identidad del firmante y la inclusión de la firma en el transparency log.

Añadiría también provenance de builds siguiendo SLSA. SLSA define provenance precisamente para poder relacionar un artifact construido con el código fuente y el proceso de build que lo originó.

Un release profesional podría contener:

```text
automation-ir-linux-amd64
automation-ir-darwin-arm64

checksums.txt
sbom.spdx.json
provenance.intoto.jsonl
artifact.sigstore.json
```

Eso da una señal especialmente fuerte para un proyecto destinado a interactuar con SAP y automatizaciones corporativas.

## Qué construiría como primera versión pública

Intentaría resistir la tentación de construir diez integraciones.

El primer release podría resolver **una cosa extremadamente bien**:

> Convertir cualquier proyecto UiPath en un grafo vendor-neutral de capabilities y workflows, consultable por humanos, CLI y agentes.

Internamente lo dividiría así:

```text
packages/
    ir/
    parser-uipath/
    parser-openapi/
    semantic-enrichment/
    validator/
    compiler-mcp/
    compiler-bpmn/

schemas/
    capability.schema.json
    workflow.schema.json
    policy.schema.json

cli/
    inspect
    extract
    normalize
    validate
    diff
    serve
    compile
```

El flujo sería:

```bash
autoforge extract ./uipath-project
```

y produciría:

```text
automation.lock
catalog.jsonl
graph.json
capabilities/
workflows/
```

Después:

```bash
autoforge inspect graph.json
```

podría mostrar:

```text
ProcessInvoice
├─ ReadMail
├─ ExtractAttachment
├─ ValidateInvoice
├─ SAP:GetVendor
├─ SAP:CreateInvoice
└─ ArchiveDocument
```

Y:

```bash
autoforge serve
```

levantaría un servidor MCP que expusiese únicamente las capabilities autorizadas.

Finalmente:

```bash
autoforge plan requirements.md
```

podría producir:

```text
requirements.md
      ↓
workflow.plan.yaml
      ↓
validation
      ↓
workflow.ir.yaml
      ↓
compiler
      ↓
BPMN / UiPath / Temporal
```

La IA entraría principalmente en `plan` y en el enrichment inicial. La extracción, validación, compilación, policy enforcement e idempotencia deberían permanecer deterministas.

## La oportunidad real

La parte menos diferencial sería «hacer un MCP para SAP» o «hacer un MCP para UiPath». Ambos proveedores ya están ahí. UiPath incluso permite actualmente exponer artifacts internos como MCP tools y utilizar MCP tools dentro de sus propios workflows. SAP está haciendo algo parecido con Automation Pilot e Integration Suite.

La parte interesante sería crear algo más parecido a un **LLVM para automatizaciones**.

En compiladores tradicionales:

```text
C ─────┐
C++ ───┤
Rust ──┼──► Intermediate Representation ───► machine targets
Swift ─┘
```

Tu equivalente sería:

```text
UiPath ─────┐
SAP ────────┤
BPMN ───────┤
OpenAPI ────┼──► Automation IR ───► MCP
n8n ────────┤                   ├──► UiPath
Temporal ───┤                   ├──► SAP
Custom ─────┘                   ├──► BPMN
                                └──► Temporal
```

Ese framing es mucho más potente para un proyecto público porque desacopla tres problemas que hoy suelen mezclarse:

**cómo está implementada una automatización**, **qué significa**, y **cómo puede invocarla un agente**.

La taxonomía mínima se convertiría en el contrato estable entre esas tres capas.

Y técnicamente tienes un momento interesante para hacerlo. MCP ya proporciona descubrimiento e invocación de tools, JSON Schema proporciona contratos estructurados, OpenAPI proporciona descripción machine-readable de APIs, BPMN proporciona una representación interoperable de procesos, y sistemas como Temporal muestran patrones maduros para retries, ejecución durable e idempotencia.

Lo que falta no parece ser otro protocolo de transporte. **Falta una representación operacional común suficientemente pequeña, rigurosa y reversible para que las automatizaciones empresariales se conviertan en primitives de agentes sin que el agente tenga que aprender cada plataforma.**

Ese sería el núcleo que intentaría convertir en estándar open source.

## Verified sources

| Claim | Source | Status |
|---|---|---|
| UiPath MCP servers expose RPA workflows, activities, agents and processes as tools | [UiPath docs: MCP servers](https://docs.uipath.com/agents/automation-cloud/latest/user-guide/mcp-servers) | verified |
| Agent activity tool inputs can be filled by the agent or bound to arguments | [UiPath docs: activities as tools](https://docs.uipath.com/agents/automation-cloud/latest/user-guide/tools-activities) | verified |
| `UiPath/skills` gives coding agents knowledge to build UiPath automations | [github.com/UiPath/skills](https://github.com/UiPath/skills) | verified; it is a skills repo, not a machine-readable activity metadata library |
| A standalone open-source UiPath XAML parser exists | [rpapub/xaml-parser](https://gh.r-mj.com/rpapub/xaml-parser) (PyPI `cpmf-uips-xaml`) | verified; README states CC BY 4.0, unsuitable as a code dependency |
| UiPath ReFrameWork template | [github.com/UiPath/ReFrameWork](https://github.com/UiPath/ReFrameWork) | verified, MIT |
| ProAgent: from RPA to Agentic Process Automation | [arXiv:2311.10751](https://arxiv.org/abs/2311.10751) | verified |
| FlowMind: automatic workflow generation with LLMs | [arXiv:2404.13050](https://arxiv.org/abs/2404.13050) | verified |
| WorkflowLLM: workflow orchestration capability of LLMs | [arXiv:2411.05451](https://arxiv.org/abs/2411.05451) | verified |
| "Workflow Lens" reconstructs UiPath call graphs, Apache 2.0 | none found | *unverified* |
| UiPath XAML Viewer recognises 200+ activity types | none found | *unverified* |
| MCP specification revision of July 2026 with a stateless core | none checked | *unverified* |
| SAP Integration Suite MCP tutorial of 2 November 2026 | none checked | *unverified* |
| The name "autoforge" proposed in this report | taken by several projects, e.g. [revl/autoforge](https://github.com/revl/autoforge), [open-autoforge](https://pypi.org/project/open-autoforge/) | not usable; the project is called FlowGlyph |
