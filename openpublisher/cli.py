import argparse
import json
from pathlib import Path
from .config import load_config
from .editorial import article_validation, create_draft
from .feeds import collect
from .wordpress import publish


def save_json(obj, name):
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Wrote:', path)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main(argv=None):
    parser = argparse.ArgumentParser(prog='openpublisher', description='Independent WordPress editorial draft publisher')
    parser.add_argument('--config', default='config.json')
    sub = parser.add_subparsers(dest='command', required=True)
    c = sub.add_parser('collect'); c.add_argument('--output', default='output/sources.json')
    c = sub.add_parser('generate'); c.add_argument('--sources', default='output/sources.json'); c.add_argument('--output', default='output/article.json')
    c = sub.add_parser('validate'); c.add_argument('--article', default='output/article.json')
    c = sub.add_parser('publish'); c.add_argument('--article', default='output/article.json')
    c.add_argument('--live', action='store_true'); c.add_argument('--status', choices=['draft', 'publish'], default='draft')
    c = sub.add_parser('run'); c.add_argument('--output-dir', default='output')
    c = sub.add_parser('queue'); c.add_argument('--article', default='output/article.json'); c.add_argument('--queue-file', default='output/review-queue.json')
    c = sub.add_parser('approve'); c.add_argument('--article', default='output/article.json'); c.add_argument('--reviewer', required=True); c.add_argument('--queue-file', default='output/review-queue.json')
    args = parser.parse_args(argv)
    config = load_config(args.config)
    if args.command == 'collect':
        report = collect(config); save_json(report, args.output)
        print('Collected', len(report['sources']), 'leads; feed failures:', len(report['feed_errors']))
    elif args.command == 'generate':
        article = create_draft(read_json(args.sources), config)
        save_json(article, args.output)
        print('Unreviewed draft generated. Inspect facts, sources and edit article JSON.')
    elif args.command == 'validate':
        article_validation(read_json(args.article))
        print('Article structure valid. This is NOT a factual verification.')
    elif args.command == 'publish':
        result = publish(read_json(args.article), config, live=args.live, status=args.status)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == 'run':
        directory = Path(args.output_dir)
        sources = collect(config)
        save_json(sources, directory / 'sources.json')
        article = create_draft(sources, config)
        save_json(article, directory / 'article.json')
        print('Stopped before WordPress. Review the article and publish separately.')
    elif args.command == 'queue':
        article = read_json(args.article); article_validation(article)
        path = Path(args.queue_file)
        items = read_json(path) if path.exists() else []
        if any(x.get('article', {}).get('primary_source_url') == article['primary_source_url'] for x in items):
            raise ValueError('An item with this primary source is already in the review queue')
        items.append({'state': 'pending_review', 'article': article})
        save_json(items, path)
        print('Added unreviewed draft to editorial queue.')
    elif args.command == 'approve':
        article = read_json(args.article); article_validation(article)
        article['reviewed'] = True
        article['reviewed_by'] = args.reviewer
        article_validation(article, require_review=True)
        save_json(article, args.article)
        queue_path = Path(args.queue_file)
        if queue_path.exists():
            items = read_json(queue_path)
            for item in items:
                queued = item.get('article', {})
                if queued.get('primary_source_url') == article['primary_source_url']:
                    item.update({'state': 'approved', 'reviewed_by': args.reviewer})
                    item['article'] = article
            save_json(items, queue_path)
        print('Human approval recorded. Publishing still requires an explicit publish command.')

if __name__ == '__main__':
    main()
