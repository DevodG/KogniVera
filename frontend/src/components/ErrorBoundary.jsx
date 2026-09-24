import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="card" style={{ border: "1px solid var(--red)", margin: "20px 0" }}>
          <h2 style={{ color: "var(--red)", marginBottom: 8 }}>Something went wrong rendering this view</h2>
          <p className="card__sub">
            {this.state.error?.message || "An unexpected error occurred."}
          </p>
          <pre
            className="mono tiny"
            style={{
              background: "var(--navy-900)",
              padding: 12,
              borderRadius: 6,
              overflow: "auto",
              color: "var(--text-dim)",
              maxHeight: 180,
            }}
          >
            {String(this.state.error?.stack || this.state.error)}
          </pre>
          <div className="row" style={{ marginTop: 14 }}>
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
            >
              Reload application
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
