"""Build every redesigned figure (PNG + SVG + PDF) into output/."""

try:
    from . import fig5_stance, fig6_themes, fig7_meso, fig8_realworld
    from . import style as S
except ImportError:
    import fig5_stance
    import fig6_themes
    import fig7_meso
    import fig8_realworld
    import style as S

BUILDERS = [
    ("fig5_net_stance", fig5_stance.build),
    ("fig6_theme_prevalence", fig6_themes.build),
    ("fig7_meso_diverging", fig7_meso.build),
    ("fig8_realworld_vs_discourse", fig8_realworld.build),
]


def main():
    for name, build in BUILDERS:
        fig = build()
        S.save(fig, name)
        print(f"saved {name}  (png/svg/pdf)")


if __name__ == "__main__":
    main()
