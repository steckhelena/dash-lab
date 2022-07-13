from jinja2 import Template


def fill_template(
    template_file: str, output_file: str, dash_root: str, defaults_root: str
):
    with open(template_file, "r") as f:
        template = Template(f.read())

    template_output = template.render(
        root_dash_path=dash_root, godash_defaults_path=defaults_root
    )

    with open(output_file, "w") as f:
        f.write(template_output)
