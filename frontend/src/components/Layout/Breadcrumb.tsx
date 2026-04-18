import { Link } from "react-router-dom";

export interface BreadcrumbItem {
  label: string;
  to?: string;
}

interface Props {
  items: BreadcrumbItem[];
}

export default function Breadcrumb({ items }: Props) {
  return (
    <nav className="breadcrumb" aria-label="Breadcrumb">
      {items.map((item, idx) => {
        const isLast = idx === items.length - 1;
        return (
          <span key={idx} className="breadcrumb-item">
            {idx > 0 && <span className="breadcrumb-sep">/</span>}
            {item.to && !isLast ? (
              <Link to={item.to} className="breadcrumb-link">
                {item.label}
              </Link>
            ) : (
              <span className={isLast ? "breadcrumb-current" : "breadcrumb-link"}>
                {item.label}
              </span>
            )}
          </span>
        );
      })}
    </nav>
  );
}
