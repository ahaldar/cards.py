import os
import sys
import argparse
import csv
import errno
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


def content_from_template(data, template):
    """
    Returns the contents of the template with all template fields replaced by
    any matching fields in the provided data.
    """
    content = template

    for field in data:
        content = content.replace('{{%s}}' % str(field), data[field])

    return content


def main(argv):
    parser = argparse.ArgumentParser(
        description='Generate printable sheets of cards')

    parser.add_argument('-f', '--filename',
                        dest='filename',
                        help='The path to a CSV file containing card data',
                        required=True)

    parser.add_argument('-t', '--template',
                        dest='template',
                        help='The path to a card template',
                        required=True)

    parser.add_argument('-T', '--title',
                        dest='title',
                        help='The title of the generated cards',
                        required=False)

    parser.add_argument('-D', '--description',
                        dest='description',
                        default='Pages generated by cards.py',
                        help='The description of the generated cards',
                        required=False)

    parser.add_argument('-C', '--disable-cut-lines',
                        dest='disable_cut_lines',
                        action='store_true',
                        default=False,
                        help='Disable cut guides on the margins of the pages',
                        required=False)

    args = vars(parser.parse_args())

    data = args['filename']
    template = args['template']
    title = args['title']
    description = args['description']

    disable_cut_lines = bool(args['disable_cut_lines'])

    with open(data) as f:
        data = csv.DictReader(f)

        with open(template) as t:
            template = t.read().strip()

        if len(template) == 0:
            print('The provided template appears to be empty. No cards will be generated.')

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
            count = int(row.get('@count', 1))

            if count < 0:
                count = 1

            for i in range(count):
                cards += card.replace('{{content}}',
                                      content_from_template(row, template))

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

            index = index.replace('{{title}}', title)
            index = index.replace('{{description}}', description)
            index = index.replace('{{pages}}', pages)

            result.write(index)

        shutil.copyfile('template/index.css', 'generated/index.css')

if __name__ == "__main__":
    main(sys.argv)
