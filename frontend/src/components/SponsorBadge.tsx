export default function SponsorBadge() {
  return (
    <div className="sponsors">
      <span className="sponsors-label">powered by</span>
      <div className="sponsors-row">
        <a
          href="https://neo4j.com"
          target="_blank"
          rel="noopener noreferrer"
          className="sponsor gold"
        >
          Neo4j
        </a>
        <a
          href="https://tessl.io"
          target="_blank"
          rel="noopener noreferrer"
          className="sponsor gold"
        >
          Tessl
        </a>
        <a
          href="https://cast.ai"
          target="_blank"
          rel="noopener noreferrer"
          className="sponsor gold"
        >
          Kimchi
        </a>
        <a
          href="https://hackersquad.dev"
          target="_blank"
          rel="noopener noreferrer"
          className="sponsor silver"
        >
          HackerSquad
        </a>
      </div>
    </div>
  );
}
