
{%- macro autosummary(items, rubric) -%}
{%- if items %}
.. rubric:: {{rubric}}
.. autosummary::
   {%- if rubric == "Content" %}
       :nosignatures:
   {%- endif %}
   {% for item in items %}
       {{item}}
   {% endfor %}
{%- endif %}
{% endmacro %}


{{ fullname | escape | underline }}

{% if all %}
.. automodule:: {{ fullname }}

{{ autosummary(all, "Content") }}
{% else %}

.. automodule:: {{ fullname }}


{%- block classes %}
{{- autosummary(classes, "Classes") }}
{%- endblock %}

{%- block functions %}
{{- autosummary(functions, "Functions") }}
{%- endblock %}

{%- block exceptions %}
{{- autosummary(exceptions, "Exceptions") }}
{%- endblock %}

..

{% if classes %}
{%- for item in classes %}
   .. autoclass:: {{ item }}
      :show-inheritance:
      :members:
      :private-members:
      :special-members:
      :exclude-members: __repr__, __str__, __init__, __weakref__
{%- endfor %}
{%- endif %}

{%- if functions %}
{%- for item in functions %}
   .. autofunction:: {{ item }}
{%- endfor %}
{%- endif %}

{%- if exceptions %}
{%- for item in exceptions %}
   .. autoexception:: {{ item }}
{%- endfor %}
{%- endif %}

{%- endif %}
