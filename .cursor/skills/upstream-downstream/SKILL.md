---
name: upstream-downstream
description: Guide for using upstream and downstream variables and conditional content in AsciiDoc modules. Use when writing, editing, or reviewing .adoc files, when using product names, CLI commands, namespaces, or operator names in documentation, or when adding build-specific content for upstream (Forklift) vs downstream (MTV).
---

# Upstream & Downstream Authoring

## Golden Rule

Never hardcode a product name, CLI tool, namespace, or operator name. Always use the corresponding variable.

## Variable Definitions

Downstream values live in `documentation/modules/common-attributes.adoc`.
Upstream overrides live in `_config.yml` under `asciidoctor.attributes`.

Upstream builds load `common-attributes.adoc` first, then `_config.yml` overrides. Any variable **not** overridden in `_config.yml` leaks the downstream value into upstream.

## Variable Quick Reference

| Variable | Upstream (Forklift) | Downstream (MTV) |
|---|---|---|
| `{build}` | upstream | downstream |
| `{project-full}` | Forklift | Migration Toolkit for Virtualization |
| `{project-short}` | Forklift | MTV |
| `{project-first}` | Forklift | Migration Toolkit for Virtualization (MTV) |
| `{virt}` | KubeVirt | OpenShift Virtualization |
| `{a-virt}` | a KubeVirt | an OpenShift Virtualization |
| `{ocp}` | OKD | Red Hat OpenShift |
| `{ocp-short}` | OKD | OpenShift |
| `{oc}` | kubectl | oc |
| `{namespace}` | konveyor-forklift | openshift-mtv |
| `{operator}` | forklift-operator | mtv-operator |
| `{operator-name}` | Forklift Operator | MTV Operator |
| `{rhv-full}` | oVirt | Red Hat Virtualization |
| `{rhv-short}` | oVirt | RHV |
| `{a-rhv}` | an oVirt | a Red Hat Virtualization |
| `{manager}` | Engine | Manager |
| `{must-gather}` | quay.io/kubev2v/forklift-must-gather:latest | registry.redhat.io/.../mtv-must-gather-rhel8:{project-z-version} |
| `{vmw}` | *(not overridden)* | VMware |

### Downstream-only variables (no upstream override)

These exist only in `common-attributes.adoc` and are safe to use inside `ifeval::["{build}" == "downstream"]` blocks:

- `{operator-name-ui}` — Migration Toolkit for Virtualization Operator
- `{ocp-name}` — OpenShift
- `{ocp-version}` — e.g. 4.21
- `{ocp-doc}` — link prefix to Red Hat OCP docs
- `{project-version}` — e.g. 2.11
- `{project-z-version}` — e.g. 2.11.0
- `{mtv-plan}`, `{mtv-mig}` — Red Hat doc URLs

## Conditional Content

### Build-based conditionals (`ifeval`)

Use `ifeval` to show content only in one build:

```asciidoc
ifeval::["{build}" == "upstream"]
This sentence appears only in the Forklift (upstream) docs.
endif::[]

ifeval::["{build}" == "downstream"]
This sentence appears only in the MTV (downstream) docs.
endif::[]
```

**Critical syntax note:** The variable must be wrapped in curly braces — `"{build}"`, not `"build"`. Without braces the condition compares a literal string and silently never matches.

### Provider-specific conditionals (`ifdef`)

Modules reused across providers use `ifdef` guards. The attribute is set by the parent assembly via `:context:`.

Provider attributes: `vmware`, `rhv`, `ova`, `ostack`, `cnv`

```asciidoc
ifdef::vmware[]
= Adding a {vmw} vSphere source provider
endif::[]
ifdef::rhv[]
= Adding {a-rhv} source provider
endif::[]
```

### UI vs CLI conditionals

```asciidoc
ifdef::web[]
. In the {ocp-short} web console, navigate to *Migration* > *Plans*.
endif::[]
ifdef::cli[]
. Run `{oc} get plans -n {namespace}`.
endif::[]
```

### Context management in assemblies

Assemblies must save and restore `:context:` so nested includes don't clobber each other:

```asciidoc
ifdef::context[:parent-context: {context}]
:context: vmware

\include::modules/adding-source-provider.adoc[leveloffset=+1]

ifdef::parent-context[:context: {parent-context}]
ifndef::parent-context[:!context:]
```

## Variables in Code Blocks

Variables are **not** expanded inside literal blocks by default. Add the `subs` attribute:

```asciidoc
[source,terminal,subs="attributes+"]
----
$ {oc} get pods -n {namespace}
----
```

For combined substitutions:

```asciidoc
[options="nowrap" subs="+quotes,+attributes"]
----
$ {oc} get migration -n {namespace}
----
```

## Common Pitfalls

1. **"Red Hat {virt}"** — renders as "Red Hat KubeVirt" upstream. Wrap in a build conditional or use a dedicated variable.
2. **Downstream-only variables in shared content** — if a variable has no upstream override (e.g. `{vmw}`), using it outside a downstream guard produces unexpected output upstream.
3. **Forgetting `subs="attributes+"`** — variables appear as literal `{oc}` in code blocks without it.
4. **Missing braces in `ifeval`** — `ifeval::["build" == "upstream"]` is always false; correct form is `ifeval::["{build}" == "upstream"]`.
5. **Hardcoded "oc" or "kubectl"** — always use `{oc}` so the right CLI tool renders per build.
6. **Hardcoded namespace** — always use `{namespace}` instead of writing `openshift-mtv` or `konveyor-forklift`.

## Module ID Convention

Module IDs must include the `{context}` suffix so the same module can be included in multiple contexts without ID collision:

```asciidoc
[id="adding-source-provider_{context}"]
= Adding a source provider
```
