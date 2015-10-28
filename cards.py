import os
import sys
import argparse
import csv
import errno
import re
import shutil


def create_missing_directories_if_necessary(path):
    """
    Mimics the command 'mkdir -p'.
    """
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def replace_image_fields_with_image_tags(string):
    """
    Recursively finds all {{image:size}} fields and returns a string replaced
    with HTML compliant <img> tags.
    """
    for match in re.finditer('{{(.*?)}}', string, re.DOTALL):
        image_path = match.group(1)

        if len(image_path) > 0:
            # determine whether a size has been explicitly specified; e.g.
            # images/name-of-image.svg:16x16
            size_index = image_path.rfind(':')

            explicit_width = None
            explicit_height = None

            if size_index is not -1:
                size = image_path[size_index + 1:]
                size = size.split('x')

                if len(size) > 1:
                    explicit_width = int(size[0])
                    explicit_height = int(size[1])

                    if explicit_width < 0:
                        explicit_width = None

                    if explicit_height < 0:
                        explicit_height = None

                if (explicit_width is not None and
                   explicit_height is not None):
                        image_tag = '<img src="{0}" width="{1}" height="{2}">'
                        image_tag = image_tag.format(image_path[:size_index],
                                                     explicit_width,
                                                     explicit_height)
            else:
                image_tag = '<img src="{0}">'.format(image_path)

            string = string[:match.start()] + image_tag + string[match.end():]

            # since the string we're finding matches on has just been changed,
            # we have to recursively look for more fields if there are any
            string = replace_image_fields_with_image_tags(string)

            break

    return string


def content_from_template(data, template):
    """
    Returns the contents of the template with all template fields replaced by
    any matching fields in the provided data.
    """
    content = template

    for field in data:
        if not field.startswith('@'):
            # ignore special variable columns
            field_value = str(data[field])
            # replace any special image fields with html compliant <img> tags
            field_value = replace_image_fields_with_image_tags(field_value)

            # finally populate the template field with the resulting value
            content = content.replace('{{%s}}' % str(field), field_value)

    return content


def colorize_help_description(help_description, required):
    apply_red_color = '\x1B[31m'
    apply_yellow_color = '\x1B[33m'
    apply_normal_color = '\033[0m'

    if required:
        help_description = apply_red_color + help_description
    else:
        help_description = apply_yellow_color + help_description

    return help_description + apply_normal_color


def main(argv):
    parser = argparse.ArgumentParser(
        description='Generate printable sheets of cards.')

    parser.add_argument('-f', '--filename',
                        dest='filename',
                        help=colorize_help_description(
                            'A path to a CSV file containing card data',
                            required=True),
                        required=True)

    parser.add_argument('-t', '--template',
                        dest='template',
                        help=colorize_help_description(
                            'A path to a card template',
                            required=True),
                        required=True)

    parser.add_argument('-T', '--title',
                        dest='title',
                        help=colorize_help_description(
                            'The title of the generated cards',
                            required=False),
                        required=False)

    parser.add_argument('-D', '--description',
                        dest='description',
                        default='Pages generated by cards.py',
                        help=colorize_help_description(
                             'The description of the generated cards',
                             required=False),
                        required=False)

    parser.add_argument('-V', '--version-identifier',
                        dest='version_identifier',
                        default='',
                        help=colorize_help_description(
                             'A version identifier that is put on'
                             ' each generated card. Requires that the template'
                             ' provides a {{version}} field.',
                             required=False),
                        required=False)

    parser.add_argument('--disable-cut-lines',
                        dest='disable_cut_lines',
                        action='store_true',
                        default=False,
                        help=colorize_help_description(
                            'Disable cut guides on the margins of the '
                             'generated pages',
                             required=False),
                        required=False)

    args = vars(parser.parse_args())

    # required arguments
    data_path = args['filename']
    default_template_path = args['template']

    # optional arguments
    title = args['title']
    description = args['description']
    version_identifier = args['version_identifier']
    disable_cut_lines = bool(args['disable_cut_lines'])

    with open(data_path) as f:
        data = csv.DictReader(f)

        with open(default_template_path) as t:
            default_template = t.read().strip()

        if len(default_template) == 0:
            print('The provided template appears to be empty. '
                  'No cards will be generated.')

            return

        with open('template/page.html') as p:
            page = p.read()

            if disable_cut_lines:
                page = page.replace('{{style}}', 'style="display: none"')
            else:
                page = page.replace('{{style}}', '')

        with open('template/card.html') as c:
            card = c.read()

        with open('template/index.html') as i:
            index = i.read()

        cards = ''
        pages = ''

        cards_on_page = 0
        cards_on_all_pages = 0

        max_cards_per_page = 9

        pages_total = 0

        for row in data:
            # determine how many instances of this card to generate (defaults
            # to a single instance if not specified)
            count = int(row.get('@count', 1))

            if count < 0:
                # if a negative count is specified, treat it as none
                count = 0

            for i in range(count):
                # determine which template to use for this card (defaults to
                # the template specified from the --template option)
                template_path = row.get('@template', default_template_path)

                if (template_path is not default_template_path and
                   len(template_path) > 0):
                    if not os.path.isabs(template_path):
                        # if the template path is not an absolute path, assume
                        # that it's located relative to where the data is
                        template_path = os.path.join(
                            os.path.dirname(data_path),
                            template_path)

                    with open(template_path) as t:
                        template = t.read().strip()
                else:
                    # if the template path points to the same template as
                    # provided throuh --template, we already have it available
                    template = default_template

                card_content = content_from_template(row, template)
                card_content = card_content.replace(
                    '{{card_index}}', str(cards_on_all_pages + 1))
                card_content = card_content.replace(
                    '{{version}}', version_identifier)

                cards += card.replace(
                    '{{content}}', card_content)

                cards_on_page += 1
                cards_on_all_pages += 1

                if cards_on_page == max_cards_per_page:
                    pages += page.replace('{{cards}}', cards)

                    pages_total += 1

                    cards_on_page = 0
                    cards = ''

        if cards_on_page > 0:
            pages += page.replace('{{cards}}', cards)

            pages_total += 1

        create_missing_directories_if_necessary('generated')

        with open('generated/index.html', 'w') as result:
            if not title or len(title) == 0:
                title = 'cards.py: {0} card(s), {1} page(s)'.format(
                    cards_on_all_pages,
                    pages_total)

            pages = pages.replace('{{cards_total}}', str(cards_on_all_pages))

            index = index.replace('{{title}}', title)
            index = index.replace('{{description}}', description)
            index = index.replace('{{pages}}', pages)

            result.write(index)

        shutil.copyfile('template/index.css', 'generated/index.css')

        print('Generated {0} card(s) on {1} page(s). '
              'See \'generated/index.html\''
              .format(cards_on_all_pages, pages_total))

if __name__ == "__main__":
    main(sys.argv)
