---
title: Forklift
layout: default
tags: [mtv, openshift virtualization, upstream, documentation]
---

## Forklift documentation

### Released documents

The following documents are official releases.

<table style="width:100%">
  <tr>
    <th>Document</th>
    <th>Format/release</th>
  </tr>

{% for doc in site.data.versioned %}

  <tr>

    {% assign mydoc = doc[1].name %}
    {% for release in site.data.releases %}
      {% assign version = release[1] %}
      {% if forloop.first  %}
        <td>{{ mydoc }}</td>
        <td>
          <div class="menu-wrap">
            <nav class="menu">
              <ul class="clearfix">
                <li>
                  <a href="#">Format/Release <span class="arrow">&#9660;</span></a>
                  <ul class="sub-menu">
      {% endif %}
      {% if release[1].name == mydoc %}
                    <li>
                      <a href="{{ version.folder }}.html"><i class="fab fa-html5"></i> HTML {{ version.release }}</a> </li><li> <a href="{{ version.folder }}.pdf"><i class="fas fa-file-pdf"></i> PDF {{ version.release }}</a>
                    </li>
      {% endif %}
    {% endfor %}
                  </ul>
              </li>
              </ul>
            </nav>
          </div>
        </td>

  </tr>
  {% endfor %}

{% for doc in site.data.static %}

  <tr>

    {% assign mydoc = doc[1].name %}
    {% for release in site.data.static %}
      {% assign version = release[1] %}
      {% if forloop.first  %}
        <td>{{ mydoc }}</td>
        <td>
          <div class="menu-wrap">
            <nav class="menu">
              <ul class="clearfix">
                <li>
                  <a href="#">Format <span class="arrow">&#9660;</span></a>
                  <ul class="sub-menu">
      {% endif %}
      {% if release[1].name == mydoc %}
                    <li>
                      <a href="{{ version.folder }}.html"><i class="fab fa-html5"></i> HTML</a> </li><li> <a href="{{ version.folder }}.pdf"><i class="fas fa-file-pdf"></i> PDF</a>
                    </li>
      {% endif %}
    {% endfor %}
                  </ul>
              </li>
              </ul>
            </nav>
          </div>
        </td>

  </tr>
  {% endfor %}

</table>


### Draft documents

The following documents are drafts.

<table style="width:100%">
  <tr>
    <th>Document</th>
    <th>Format/release</th>
  </tr>

{% for doc in site.data.devprev %}

  <tr>

    {% assign mydoc = doc[1].name %}
    {% for release in site.data.devprev %}
      {% assign version = release[1] %}
      {% if forloop.first  %}
        <td>{{ mydoc }}</td>
        <td>
          <div class="menu-wrap">
            <nav class="menu">
              <ul class="clearfix">
                <li>
                  <a href="#">Format <span class="arrow">&#9660;</span></a>
                  <ul class="sub-menu">
      {% endif %}
      {% if release[1].name == mydoc %}
                    <li>
                      <a href="{{ version.folder }}.html"><i class="fab fa-html5"></i> HTML</a> </li><li> <a href="{{ version.folder }}.pdf"><i class="fas fa-file-pdf"></i> PDF</a>
                    </li>
      {% endif %}
    {% endfor %}
                  </ul>
              </li>
              </ul>
            </nav>
          </div>
        </td>

  </tr>
  {% endfor %}

</table>

> error ""
> Documents in this section are works in progress.
