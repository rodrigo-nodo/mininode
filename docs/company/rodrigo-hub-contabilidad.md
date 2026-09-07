# Rodrigo Hub - Contabilidad y operación tributaria inicial

## Objetivo

Mantener una operación contable simple, trazable y automatizable para **Rodrigo Hub SpA**, sin mezclarla con la contabilidad de futuras sociedades como Rodrigo Tech.

## Régimen recomendado

Propuesta inicial:

- **Régimen tributario:** Pro Pyme General.
- **Tipo de contabilidad:** contabilidad simplificada.
- **IVA:** servicios digitales y software se tratarán según las reglas vigentes aplicables a cada operación.
- **PPM:** revisar y declarar mensualmente junto con el F29 cuando corresponda.

La decisión definitiva debe validarse al momento de iniciar actividades, considerando requisitos vigentes y situación real de la sociedad.

## Principio operativo

**Separar completamente el dinero personal del dinero de Rodrigo Hub SpA.**

Recomendación:

- cuenta bancaria exclusiva para Hub;
- todos los ingresos de clientes entran a esa cuenta;
- los gastos de Hub se pagan desde esa cuenta;
- aportes de Rodrigo deben identificarse como capital o préstamo;
- retiros, remuneraciones y devoluciones de préstamos deben registrarse correctamente.

## Flujo mensual esperado

```text
Banco + SII + pasarela
        ↓
Conciliación
        ↓
Libro de Caja
        ↓
IVA / PPM esperado
        ↓
Comparar con propuesta SII
        ↓
Revisión Rodrigo
        ↓
F29
```

La meta es automatizar cálculo y control, manteniendo inicialmente una revisión humana antes de declarar.

## Matriz contable resumida

| Frecuencia | Control / obligación | Fuente principal | Automatizable | Responsable inicial |
|---|---|---|---|---|
| Una vez | Inicio de actividades y régimen | SII | Parcial | Rodrigo + validación contador |
| Una vez | Capital inicial | Estatuto + banco | No | Rodrigo |
| Continua | Emitir documentos tributarios | SII / pasarela | Alta | Sistema + Rodrigo |
| Continua | Respaldo de gastos | DTE / documentos | Alta para DTE | Rodrigo |
| Mensual | Registro de Compras y Ventas | SII | Alta | Revisar |
| Mensual | Conciliación bancaria | Banco + RCV | Alta | Rodrigo / sistema |
| Mensual | Libro de Caja | Banco + RCV + otros | Alta | Rodrigo / sistema |
| Mensual | IVA | RCV | Alta | Revisar |
| Mensual | PPM | Ventas | Alta | Revisar |
| Mensual | F29 | SII + RCV + PPM + retenciones | Alta | Rodrigo, con revisión inicial |
| Mensual | P&L por producto | Sistema interno | Alta | Rodrigo |
| Trimestral | Revisión tributaria | Información consolidada | Parcial | Contador recomendado |
| Anual | Cierre y declaraciones juradas | SII + registros internos | Parcial | Rodrigo + contador |
| Anual | F22 | SII + registros | Parcial | Contador recomendado |

## Gestión interna por producto

Aunque tributariamente la contabilidad sea simplificada, Hub debe mantener información de gestión separada por producto.

Ejemplo:

| Producto | Ventas | Cloud / API | Marketing | Otros costos | Margen |
|---|---:|---:|---:|---:|---:|
| Privacy Web |  |  |  |  |  |
| Privacy Data |  |  |  |  |  |
| Futuro SaaS / agente |  |  |  |  |  |

También conviene medir, según corresponda:

- MRR;
- clientes;
- churn;
- CAC;
- costo de APIs;
- margen bruto.

Esto permite conocer la rentabilidad real de cada producto y facilita una eventual venta o separación.

## Rodrigo como accionista y administrador

### Remuneración

Mientras Hub tenga ingresos bajos o inestables, no es necesario fijar una remuneración alta desde el inicio.

Cuando exista caja suficiente, puede evaluarse una remuneración razonable por el trabajo efectivamente realizado, con el tratamiento tributario y previsional que corresponda.

### Retiros / dividendos

Los retiros o dividendos no deben confundirse con gastos de la empresa.

Deben registrarse separadamente de una remuneración y tratarse según el régimen tributario vigente.

## Financiamiento de Rodrigo hacia Hub

Se recomienda separar:

### Capital

Monto permanente aportado a la sociedad.

### Préstamo de Rodrigo a Hub

Financiamiento adicional documentado que la sociedad podrá devolver cuando tenga caja.

Ejemplo:

```text
Capital inicial               $100.000
Préstamo Rodrigo → Hub        $500.000
```

Los préstamos deben tener trazabilidad y respaldo suficiente para distinguirlos de retiros o aportes de capital.

## Gastos históricos anteriores a la sociedad

No convertir automáticamente todos los gastos realizados antes de constituir Hub en deuda de la sociedad con Rodrigo.

Clasificación recomendada:

- gastos ya consumidos: revisar caso a caso, normalmente quedan como históricos personales;
- activos que todavía existen: evaluar aporte, cesión o transferencia a Hub;
- código, dominios e IP: dejar claramente documentada su titularidad o transferencia;
- dinero aportado después de constituir Hub: registrar como capital o préstamo.

## Catálogo básico de movimientos

| Movimiento | Caja | IVA | Renta | Producto / unidad |
|---|---:|---:|---:|---|
| Venta Privacy Data | Ingreso | Según operación | Ingreso | Privacy Data |
| Pago Render | Egreso | Según documento | Gasto si corresponde | Compartido |
| API IA | Egreso | Revisar proveedor | Gasto si corresponde | Producto correspondiente |
| Capital Rodrigo | Ingreso | No | No renta | Corporativo |
| Préstamo Rodrigo | Ingreso | No | No renta | Corporativo |
| Devolución préstamo | Egreso | No | No gasto | Corporativo |
| Retiro / dividendo | Egreso | No | No gasto | Corporativo |

Principio clave:

**Movimiento de caja no es lo mismo que ingreso o gasto tributario.**

## Automatización deseada

Arquitectura conceptual:

```text
SII / RCV / DTE
       │
Banco ─┼─→ Hub Accounting ←─ Pasarela
       │
       ├── conciliación
       ├── Libro de Caja
       ├── IVA esperado
       ├── PPM esperado
       ├── control F29
       └── P&L por producto
```

La automatización debe ayudar a calcular y controlar. Inicialmente, la presentación final de declaraciones debe seguir siendo revisada por Rodrigo y, en los primeros meses, por un contador.

## Rol recomendado del contador

No se propone delegar toda la operación contable.

Modelo sugerido:

- setup inicial;
- revisión mensual durante los primeros meses;
- después, revisión trimestral si el proceso está estable;
- consultas tributarias especiales;
- declaraciones juradas anuales;
- revisión del F22 y cierre anual.

## Límites relevantes del régimen

Como referencia inicial del régimen Pro Pyme General, revisar al momento de iniciar actividades:

- límite de capital efectivo al inicio;
- promedio máximo de ingresos brutos permitido;
- límite máximo de ingresos por ejercicio;
- restricciones para determinadas rentas pasivas.

Los valores y condiciones deben confirmarse con la normativa vigente al momento de la constitución e inicio de actividades.

## Estado

Documento de trabajo para la operación inicial de Rodrigo Hub SpA.

No reemplaza asesoría contable o tributaria profesional. Debe actualizarse cuando cambie el régimen, la estructura societaria, el volumen de operación o aparezcan operaciones especiales.
