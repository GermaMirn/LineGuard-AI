import { Link } from "react-router-dom";

interface BreadcrumbItem {
  label: string;
  path?: string;
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
}

export default function Breadcrumbs({ items }: BreadcrumbsProps) {
  return (
    <nav className="flex flex-col gap-2 relative z-10">
      {/* Название текущей страницы - сверху */}
      <h1 className="text-white font-bold" style={{ fontSize: '40px', lineHeight: '1.2' }}>
        {items[items.length - 1].label}
      </h1>

      {/* Навигационная цепочка - снизу */}
      <div className="flex items-center gap-2 text-sm">
        {items.map((item, index) => (
          <div key={index} className="flex items-center gap-2">
            {item.path ? (
              <Link
                to={item.path}
                className="text-white/60 hover:text-white transition-colors"
              >
                {item.label}
              </Link>
            ) : (
              <span className="text-white">{item.label}</span>
            )}

            {index < items.length - 1 && (
              <svg
                className="w-4 h-4 text-white/40"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            )}
          </div>
        ))}
      </div>
    </nav>
  );
}

