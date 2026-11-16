# Arquitectura v2: C4 del módulo comercial

Complementa el [análisis de impacto](../analisis-impacto-modulo-comercial.md). Los diagramas están
en Mermaid para que se vean en GitHub y se revisen como código.

**Leyenda de colores (componentes):** verde = nuevo · amarillo = extensión de un punto previsto ·
azul = sin cambio. Los tres diagramas son *Propuesto*: el módulo se construye en el Corte 3.

> La versión 1 de los diagramas C4 (contexto, contenedores y componentes del núcleo) está descrita en
> el documento de arquitectura v1 del Drive; sus figuras no están versionadas en este repositorio.
> La sección «Qué cambia frente a la v1» resume la diferencia en texto.

## Nivel 1 · Contexto

```mermaid
flowchart LR
    consumidor(["Consumidor<br/>consulta y compara"])
    reportante(["Reportante<br/>registra precios"])
    comercio(["Comercio (voluntario)<br/>precios oficiales y promociones"])
    moderador(["Moderador<br/>verifica y modera"])

    sistema["AhorraPues<br/>plataforma de comparación de precios"]

    sipsa["SIPSA - DANE<br/>precios de referencia"]
    correo["Servicio de correo<br/>recuperación de contraseña"]

    consumidor --> sistema
    reportante --> sistema
    comercio -->|"NUEVO en v2"| sistema
    moderador --> sistema
    sistema --> sipsa
    sistema --> correo

    classDef nuevo fill:#d9f2e3,stroke:#1c7a3d,color:#10311d
    classDef base fill:#e8effb,stroke:#4a6fa5,color:#14213d
    class comercio nuevo
    class consumidor,reportante,moderador,sistema,sipsa,correo base
```

El único actor nuevo es el **Comercio**; ya estaba previsto como actor desde el Corte 1.

## Nivel 2 · Contenedores

No cambia ningún contenedor: el portal de comercios es parte de la misma aplicación Django.

```mermaid
flowchart TB
    navegador["Interfaz web móvil y de escritorio<br/>HTML + HTMX"]
    subgraph app ["Aplicación web Django (monolito modular)"]
        nucleo["Módulos del núcleo<br/>cuentas, catalogo, establecimientos,<br/>precios, comparacion, moderacion, integraciones"]
        comercios["Módulo comercios<br/>perfil, precio oficial, promociones"]
    end
    bd[("PostgreSQL 16")]
    cache[("Redis 7<br/>caché por producto")]

    navegador --> app
    comercios -.->|"se registra al arrancar"| nucleo
    app --> bd
    app --> cache

    classDef nuevo fill:#d9f2e3,stroke:#1c7a3d,color:#10311d
    classDef base fill:#e8effb,stroke:#4a6fa5,color:#14213d
    class comercios nuevo
    class navegador,nucleo,bd,cache base
```

## Nivel 3 · Componentes del módulo comercial y su integración

Muestra la **opción B** del análisis de impacto (DP-1): `comparacion` no importa `comercios`; el
módulo comercial se registra mediante un puerto. Si el equipo elige la opción A, la flecha punteada
se reemplaza por una importación directa y el contrato `comercios-no-adelantado` se relaja.

```mermaid
flowchart TB
    subgraph com ["apps/comercios (NUEVO)"]
        portal["Portal de comercios<br/>vistas HTMX"]
        apicom["API de comercios<br/>OpenAPI"]
        servcom["Servicios<br/>perfil, verificación, precio oficial, promociones"]
        domprom["Dominio de promociones<br/>DescuentoPorcentual, PrecioEspecial, PagueXLleveY"]
        selcom["Selector comercial<br/>oficiales y promociones vigentes"]
        modcom[("Modelos<br/>PerfilComercio, PrecioOficial,<br/>Promocion, SolicitudCorreccion")]
    end

    subgraph comp ["apps/comparacion"]
        puerto["Puerto de complementos<br/>(propuesto, opción B)"]
        selcmp["Selector de comparación<br/>FilaComparacion"]
        ranking["domain/ranking.py<br/>orden neutral"]
        vista["Vista, plantilla y serializer público"]
    end

    cuentas["cuentas.services<br/>asignar rol comercio"]
    cache["core.cache<br/>invalidar_comparacion"]

    portal --> servcom
    apicom --> servcom
    servcom --> domprom
    servcom --> modcom
    servcom --> cuentas
    servcom --> cache
    selcom --> modcom
    selcom -.->|"implementa"| puerto
    selcmp --> puerto
    selcmp --> ranking
    vista --> selcmp

    classDef nuevo fill:#d9f2e3,stroke:#1c7a3d,color:#10311d
    classDef ext fill:#fff1c9,stroke:#a77b00,color:#3d2f00
    classDef base fill:#e8effb,stroke:#4a6fa5,color:#14213d
    class portal,apicom,servcom,domprom,selcom,modcom nuevo
    class puerto,selcmp,vista,cuentas ext
    class ranking,cache base
```

`domain/ranking.py` aparece en azul a propósito: es la única función que ordena y **no se modifica**
(EC-06). Los datos comerciales viajan junto al resultado, nunca dentro de la clave de orden.

## Qué cambia frente a la v1

| Elemento | v1 (núcleo, Corte 2) | v2 (con módulo comercial) |
|---|---|---|
| Actores | Consumidor, reportante, moderador | + Comercio (voluntario) |
| Contenedores | App Django, PostgreSQL, Redis, interfaz web | **Iguales** |
| Módulos de la app | 7 módulos del núcleo | + `comercios` (nuevo) |
| Orden de la comparación | `_clave_neutral` | **Igual** (sin cambios) |
| Origen del precio mostrado | Solo reportes (y referencia SIPSA aparte) | Oficial verificado o reportado (ADR-018), con advertencia de discrepancia |
| Promociones | Bandera `es_promocion` sin uso | Etiqueta con condiciones (ADR-014) y, según D-3, arreglo aparte |
| Dependencias entre módulos | El núcleo no conoce `comercios` | Igual con la opción B; con la A, el contrato se relaja |
| Caché | Por producto, TTL 60 s | Igual; `comercios` invalida al publicar |
| Migraciones | — | Solo la inicial de `comercios`; ninguna sobre tablas existentes |
