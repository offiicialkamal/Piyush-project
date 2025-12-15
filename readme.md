```mermaid
flowchart TD
    A[main.py] -->|Pass cookies| B[core/main.py]

    B -->|Split by speed / threads| C1[Thread 1]
    B -->|Split by speed / threads| C2[Thread 2]
    B -->|Split by speed / threads| C3[Thread N]

    C1 -->|Iterate cookies| D1[Extract Token & Data]
    C2 -->|Iterate cookies| D2[Extract Token & Data]
    C3 -->|Iterate cookies| D3[Extract Token & Data]

    D1 --> E[core/profile]
    D2 --> F[core/id]
    D3 --> E

    E -->|Fetch data & post comment| G[Facebook]
    F -->|Fetch data & post comment| G

    %% Styling (GitHub safe)
    style A fill:#1f2937,color:#ffffff,stroke:#111827,stroke-width:2px
    style B fill:#2563eb,color:#ffffff,stroke:#1e40af,stroke-width:2px

    style C1 fill:#0284c7,color:#ffffff
    style C2 fill:#0284c7,color:#ffffff
    style C3 fill:#0284c7,color:#ffffff

    style D1 fill:#16a34a,color:#ffffff
    style D2 fill:#16a34a,color:#ffffff
    style D3 fill:#16a34a,color:#ffffff

    style E fill:#9333ea,color:#ffffff
    style F fill:#9333ea,color:#ffffff

    style G fill:#dc2626,color:#ffffff,stroke-width:2px
