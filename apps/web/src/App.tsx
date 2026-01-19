function App() {
  return (
    <div
      style={{
        minHeight: "100vh",
        margin: 0,
        padding: "2rem",
        fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        backgroundColor: "#0f172a",
        color: "#e5e7eb",
      }}
    >
      <div
        style={{
          maxWidth: "960px",
          margin: "0 auto",
        }}
      >
        <header style={{ marginBottom: "2rem" }}>
          <h1
            style={{
              fontSize: "2rem",
              fontWeight: 600,
              marginBottom: "0.25rem",
            }}
          >
            InquiryOS – AI Research Workspace
          </h1>
          <p
            style={{
              color: "#9ca3af",
              fontSize: "0.95rem",
            }}
          >
            A multi-agent research environment for planning, searching, reading,
            and synthesizing answers with traceable sources.
          </p>
        </header>

        <main>
          <section
            style={{
              padding: "1.5rem",
              borderRadius: "0.75rem",
              backgroundColor: "#020617",
              border: "1px solid #1f2937",
            }}
          >
            <h2
              style={{
                fontSize: "1.125rem",
                fontWeight: 500,
                marginBottom: "0.75rem",
              }}
            >
              New Research Run
            </h2>
            <p
              style={{
                fontSize: "0.9rem",
                color: "#9ca3af",
              }}
            >
              The UI will go here. Soon, you&apos;ll be able to ask complex
              questions and see full research plans, sources, and synthesized
              answers.
            </p>
          </section>
        </main>
      </div>
    </div>
  );
}

export default App;
