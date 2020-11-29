# Forklift

Forklift is the upstream project for Migration Toolkit for Virtualization.

## Contributing

Read the [Guidelines for Red Hat Documentation](https://redhat-documentation.github.io/) before opening a pull request.

### Upstream and downstream variables

Use the following variables:

| Variable | Upstream value | Downstream value |
| -------- | -------------- | ---------------- |
| project-full | Forklift   | Migration Toolkit for Virtualization |
| project-short | Forklift | MTV |
| project-version | 2.0-beta | 2.0-beta |
| virt | KubeVirt | OpenShift Virtualization |
| ocp | OpenShift Kubernetes Engine | Red Hat OpenShift Container Platform |
| ocp-version   | 4.6 | 4.6 |
| ocp-short | OKE | OCP |

Variables cannot be used in CLI commands or code blocks unless you include the "attributes" keyword:

	[options="nowrap" subs="+quotes,+attributes"]
	----
	# ls {VariableName}
	----

You can hide or show specific blocks, paragraphs, warnings or chapters with the `build` variable. Its value can be set to "downstream" or "upstream":

	ifeval::["build" == "upstream"]
	This content is only relevant for Forklift.
	endif::[]

### Building a document preview

You can build a document preview by running a Jekyll container.

- Clone the repository, check out the `main` branch, and make your changes.
- Build the Jekyll site:

  ```console
  git clone -b source https://github.com/konveyor/forklift-documentation.git && cd forklift-documentation
  for i in .jekyll-cache _site; do mkdir ${i} && chmod 777 ${i}; done
  for i in Gemfile.lock; do touch ${i} && chmod 777 ${i}; done
  ```

- If your operating system is SELinux-enabled:

  ```console
  podman run -it --rm --name jekyll -p 4000:4000 -v $(pwd):/srv/jekyll:Z jekyll/jekyll jekyll serve --watch --future
  ```

  **NOTE**: The Z at the end of the volume (-v) will relabel its contents so that it can be written from within the container, like running `chcon -Rt svirt_sandbox_file_t -l s0:c1,c2` yourself. Be sure that you have changed your present working directory to the git cloned directory as shown above.

- If your operating system is not SELinux-enabled:

  ```console
  podman run -it --rm --name jekyll -p 4000:4000 -v $(pwd):/srv/jekyll jekyll/jekyll jekyll serve --watch --future
  ```

- Navigate to `http://0.0.0.0:4000` in a web browser to view the preview.
