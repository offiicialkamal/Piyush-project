%% Mermaid Diagram with Improved Horizontal Flow
graph LR
M[main.py] -->|Pass cookies| C(core/main.py)
C -->|Divide cookies by speed| T1(Thread 1)
C -->|Divide cookies by speed| T2(Thread 2)
C -->|Divide cookies by speed| T3(Thread 3)
T1 -->|Extract token| P(core/profile)
T2 -->|Extract token| I(core/id)
T3 -->|Extract token| I
P --> F(Facebook)
I --> F
F -->|Post comments| F2(Facebook confirmation)

    %% Styling for nodes
    style M fill:#f9f,stroke:#333,stroke-width:4px
    style C fill:#ccf,stroke:#333,stroke-width:2px
    style T1 fill:#bbf,stroke:#333,stroke-width:2px
    style T2 fill:#bbf,stroke:#333,stroke-width:2px
    style T3 fill:#bbf,stroke:#333,stroke-width:2px
    style P fill:#cfc,stroke:#333,stroke-width:2px
    style I fill:#cfc,stroke:#333,stroke-width:2px
    style F fill:#fcf,stroke:#333,stroke-width:2px
    style F2 fill:#fcf,stroke:#333,stroke-width:2px

    %% Customizing links
    linkStyle 0 stroke:#00f,stroke-width:2px
    linkStyle 1 stroke:#00f,stroke-width:2px
    linkStyle 2 stroke:#00f,stroke-width:2px
    linkStyle 3 stroke:#0f0,stroke-width:2px
    linkStyle 4 stroke:#f00,stroke-width:2px
    linkStyle 5 stroke:#f00,stroke-width:2px
