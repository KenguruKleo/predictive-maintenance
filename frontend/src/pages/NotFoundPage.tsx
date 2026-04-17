import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="page-notfound">
      <h1>404</h1>
      <p>Page not found.</p>
      <Link to="/" className="btn btn--primary">
        Go to Dashboard
      </Link>
    </div>
  );
}
