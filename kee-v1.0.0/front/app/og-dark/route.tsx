import { ImageResponse } from "next/og";

export const runtime = "edge";

const size = { width: 1200, height: 630 };

/** Dark brand promo card — /og-dark */
export async function GET() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          position: "relative",
          background: "#121211",
          fontFamily:
            'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif',
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "radial-gradient(ellipse 75% 60% at 28% 40%, #1c1c1a 0%, #141413 55%, #0e0e0d 100%)",
          }}
        />

        <div
          style={{
            position: "absolute",
            right: 72,
            top: 90,
            width: 420,
            height: 420,
            display: "flex",
            opacity: 0.45,
          }}
        >
          <svg width="420" height="420" viewBox="0 0 420 420">
            <g stroke="#4a4a44" strokeWidth="1.2" fill="none">
              <line x1="80" y1="120" x2="180" y2="70" />
              <line x1="180" y1="70" x2="290" y2="110" />
              <line x1="180" y1="70" x2="210" y2="190" />
              <line x1="80" y1="120" x2="140" y2="230" />
              <line x1="140" y1="230" x2="210" y2="190" />
              <line x1="210" y1="190" x2="300" y2="240" />
              <line x1="290" y1="110" x2="340" y2="200" />
              <line x1="300" y1="240" x2="340" y2="200" />
              <line x1="140" y1="230" x2="200" y2="320" />
              <line x1="210" y1="190" x2="200" y2="320" />
              <line x1="300" y1="240" x2="260" y2="340" />
              <line x1="200" y1="320" x2="260" y2="340" />
            </g>
            <g fill="#6a6a62">
              <circle cx="80" cy="120" r="4" />
              <circle cx="180" cy="70" r="5" />
              <circle cx="290" cy="110" r="4" />
              <circle cx="140" cy="230" r="4" />
              <circle cx="210" cy="190" r="6" />
              <circle cx="300" cy="240" r="4" />
              <circle cx="340" cy="200" r="4" />
              <circle cx="200" cy="320" r="4" />
              <circle cx="260" cy="340" r="5" />
            </g>
          </svg>
        </div>

        <div
          style={{
            position: "relative",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            padding: "0 88px",
            gap: 36,
            maxWidth: 760,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 22 }}>
            <div
              style={{
                width: 64,
                height: 64,
                background: "#b42318",
                color: "#fff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 34,
                fontWeight: 700,
                letterSpacing: "-0.04em",
                borderRadius: 4,
              }}
            >
              K
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div
                style={{
                  fontSize: 42,
                  fontWeight: 400,
                  letterSpacing: "0.04em",
                  color: "#f2f2ee",
                  lineHeight: 1,
                }}
              >
                KEE科室版
              </div>
              <div
                style={{
                  fontSize: 16,
                  letterSpacing: "0.14em",
                  color: "#8a8a84",
                  textTransform: "uppercase",
                  lineHeight: 1,
                }}
              >
                Evolution Engine
              </div>
            </div>
          </div>

          <div
            style={{
              fontSize: 28,
              fontWeight: 400,
              color: "#c4c4bc",
              lineHeight: 1.45,
              letterSpacing: "0.01em",
            }}
          >
            可演化、可信任、可被 Agent 调用的知识引擎
          </div>
        </div>
      </div>
    ),
    { ...size },
  );
}
