import java.util.List;

/** Kanagawa: three palettes, one quiet workspace. */
public final class ThemeDemo {
    private static final int DEFAULT_LIMIT = 24;
    private final String name;

    public ThemeDemo(String name) {
        this.name = name;
    }

    @Deprecated
    public String welcome(List<String> themes, boolean detailed) {
        // Wave is cool, Dragon is warm, Lotus is light.
        var palette = List.of("Wave", "Dragon", "Lotus");
        int count = Math.min(themes.size(), DEFAULT_LIMIT);

        if (detailed && count > 0) {
            return "%s: %d themes".formatted(this.name, count);
        }

        try {
            for (String theme : palette) {
                System.out.println("Welcome to " + theme);
            }
        } catch (IllegalArgumentException exception) {
            throw new IllegalStateException("Cannot load palette", exception);
        }

        return "Make something beautiful.";
    }
}
