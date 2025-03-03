# Contributing to Forklift documentation

This project is [Apache 2.0 licensed](LICENSE) and accepts contributions via
GitHub pull requests.

Read the [Guidelines for Red Hat Documentation](https://redhat-documentation.github.io/) before opening a pull request.

### Upstream and downstream variables

This document uses the following variables to ensure that upstream and downstream product names and versions are rendered correctly.

| Variable | Upstream value | Downstream value |
| -------- | -------------- | ---------------- |
| project-full | Forklift   | Migration Toolkit for Virtualization |
| project-short | Forklift | MTV |
| project-version | 2.0 | 2.0 |
| virt | KubeVirt | OpenShift Virtualization |
| ocp | OKD | Red Hat OpenShift Container Platform |
| ocp-version   | 4.7 | 4.7 |
| ocp-short | OKD | OCP |

Variables cannot be used in CLI commands or code blocks unless you include the "attributes" keyword:

	[options="nowrap" subs="+quotes,+attributes"]
	----
	# ls {VariableName}
	----

You can hide or show specific blocks, paragraphs, warnings or chapters with the `build` variable. Its value can be set to "downstream" or "upstream":

	ifeval::["build" == "upstream"]
	This content is only relevant for Forklift.
	endif::[]
