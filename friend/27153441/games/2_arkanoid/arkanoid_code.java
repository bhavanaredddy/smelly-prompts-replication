import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public class Arkanoid {
    private static final int MAX_LEVEL = 33;
    private static final int BOARD_WIDTH = 200;
    private static final int BOARD_HEIGHT = 300;
    private static final int BRICK_WIDTH = 20;
    private static final int BRICK_HEIGHT = 10;
    private static final int BALL_DIAMETER = 10;
    private static final int USER_START_LIVES = 3;

    private int level;
    private Ball ball;
    private Board board;
    private int lives;

    private static enum Color {
        BLUE,
        RED,
        GOLD,
        GREEN,
    }

    private static class Ball {
        private int x;
        private int y;
        private int speed;
        private int dx;
        private int dy;
        private int diameter;

        Ball(int x, int y) {
            this.x = x;
            this.y = y;
            this.speed = 5;
            this.dx = (int)((double)this.speed * Math.sqrt(2.0) / 2.0);
            this.dy = (int)((double)this.speed * Math.sqrt(2.0) / 2.0);
            this.diameter = BALL_DIAMETER;
        }

        void move() {
            x += dx;
            y += dy;

            if (x <= 0 || x >= BOARD_WIDTH - diameter) {
                dx = -dx;
            } else if (y <= 0) {
                dy = -dy;
            } else if (y >= BOARD_HEIGHT - diameter) {
                // Game over
            }
        }
    }

    private static class Brick {
        public int x;
        public int y;
        private int width;
        private int height;
        private Color color;
        private int hits_remaining;

        Brick(int x, int y, Color color, boolean double_brick) {
            this.x = x;
            this.y = y;
            this.width = double_brick ? BRICK_WIDTH * 2 : BRICK_WIDTH;
            this.height = BRICK_HEIGHT;
            this.color = color;
        }

        static Brick Paddle() {
            Brick paddle = new Brick(BOARD_WIDTH / 2, BOARD_HEIGHT - BRICK_HEIGHT, Color.GREEN, false);
            paddle.hits_remaining = -1;

            return paddle;
        }
    }

    private static class Board {
        private int width;
        private int height;
        private List<Brick> bricks;
        private Brick paddle;

        Board(int level) {
            this.width = BOARD_WIDTH;
            this.height = BOARD_HEIGHT;
            this.bricks = new ArrayList<>();

            Random random = new Random();

            for (int i = 0; i < 50; i++) {
                this.bricks.add(new Brick(random.nextInt(BOARD_WIDTH), random.nextInt(BOARD_HEIGHT / 3 - BRICK_HEIGHT), Color.BLUE, false));
            }

            for (int i = 0; i < level - 1; i++) {
                this.bricks.add(new Brick(random.nextInt(BOARD_WIDTH), random.nextInt(BOARD_HEIGHT / 3 - BRICK_HEIGHT), Color.RED, false));
                this.bricks.add(new Brick(random.nextInt(BOARD_WIDTH), random.nextInt(BOARD_HEIGHT / 3 - BRICK_HEIGHT), Color.RED, false));
                this.bricks.add(new Brick(random.nextInt(BOARD_WIDTH), random.nextInt(BOARD_HEIGHT / 3 - BRICK_HEIGHT), Color.GOLD, false));
            }

            this.paddle = Brick.Paddle();
        }
    }

    Arkanoid() {
        this.level = 1;
        this.ball = new Ball(0, 0);
        this.board = new Board(this.level);
        this.lives = USER_START_LIVES;
    }

    private void run() {
        while (level < MAX_LEVEL && lives > 0) {
            KeyboardKey key = KeyboardInterface.getKeyboardKey();

            if (key == KeyboardKey.LEFT) {
                if (board.paddle.x > 0) {
                    board.paddle.x -= 5;
                }
            } else if (key == KeyboardKey.RIGHT) {
                if (board.paddle.x + board.paddle.width < board.width) {
                    board.paddle.x += 5;
                }
            }

            ball.move();

            if (ball.y + ball.diameter >= board.paddle.y && ball.x >= board.paddle.x && ball.x <= board.paddle.x + board.paddle.width) {
                ball.dy = -ball.dy;
            }

            if (board.bricks.isEmpty()) {
                next_level();
            }
        }
    }

    private void next_level() {
        this.level++;
        this.ball = new Ball(0, 0);
        this.board = new Board(this.level);
    }

    public static void main(String[] args) {
        Arkanoid game = new Arkanoid();

        game.run();
    }
}
