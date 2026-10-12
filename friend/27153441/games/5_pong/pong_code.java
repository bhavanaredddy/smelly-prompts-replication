public class Pong {
    private static final int BLOCK_SIZE = 10;
    private static final int BOARD_WIDTH = 120;
    private static final int BOARD_HEIGHT = 80;
    private static final int PADDLE_WIDTH = 1;
    private static final int PADDLE_HEIGHT = 4;
    private static final int WINNING_SCORE = 10;

    private GraphicsCanvas canvas;
    private SoundEngine sound;
    private int[] scores;
    private Paddle paddle1, paddle2;
    private Ball ball;

    private static class Paddle {
        private int x, y;

        public Paddle(int x) {
            this.x = x;
            this.y = (BOARD_HEIGHT / 2 - PADDLE_HEIGHT / 2) * BLOCK_SIZE;
        }

        public void move(int dy) {
            this.y += dy;
        }
    }

    private static class Ball {
        private int x, y;
        private int dx, dy;

        public Ball(int dx) {
            this.x = BOARD_WIDTH / 2 * BLOCK_SIZE;
            this.y = BOARD_HEIGHT / 2 * BLOCK_SIZE;
            this.dx = dx;
            this.dy = 0;
        }

        public void move() {
            this.x += this.dx;
            this.y += this.dy;
        }

        public boolean hitsLeftPaddle(Paddle paddle) {
            return this.x - BLOCK_SIZE <= paddle.x && this.y >= paddle.y && this.y <= paddle.y + PADDLE_HEIGHT * BLOCK_SIZE;
        }

        public boolean hitsRightPaddle(Paddle paddle) {
            return this.x >= paddle.x && this.y >= paddle.y && this.y <= paddle.y + PADDLE_HEIGHT * BLOCK_SIZE;
        }

        public boolean hitsTopOrBottom() {
            return this.y <= 0 || this.y - BLOCK_SIZE >= BOARD_HEIGHT * BLOCK_SIZE;
        }
    }

    public Pong() {
        this.canvas = new GraphicsCanvas(BOARD_WIDTH * BLOCK_SIZE, BOARD_HEIGHT * BLOCK_SIZE);
        this.scores = new int[2];
        this.paddle1 = new Paddle(BLOCK_SIZE);
        this.paddle2 = new Paddle((BOARD_WIDTH - 1) * BLOCK_SIZE);
        this.ball = new Ball(-5);
    }

    private void update(int paddle1Dy, int paddle2Dy) {
        if (this.ball.x < 0) {
            this.scores[1]++;
        } else if (this.ball.x >= BOARD_WIDTH * BLOCK_SIZE) {
            this.scores[0]++;
        }

        if (this.ball.hitsLeftPaddle(this.paddle1) || this.ball.hitsRightPaddle(this.paddle2)) {
            this.ball.dx *= -1;
            this.ball.dx *= 1.1;
            this.ball.dy *= 1.1;
            this.sound.beep();
        }

        if (this.ball.hitsTopOrBottom()) {
            this.ball.dy *= -1;
            this.ball.dx *= 1.1;
            this.ball.dy *= 1.1;
            this.sound.beep();
        }

        this.ball.move();
        this.paddle1.move(paddle1Dy);
        this.paddle2.move(paddle2Dy);
    }

    private void showWinner(int winner) {
        this.canvas.clear();
        this.canvas.fill(Color.BLACK);

        this.canvas.drawText(
            BOARD_WIDTH / 2 - 5 * BLOCK_SIZE, BOARD_HEIGHT / 2 - 2 * BLOCK_SIZE,
            "Player " + String.valueOf(winner) + " wins!", Color.WHITE
        );

        this.canvas.show();
    }

    private void render() {
        this.canvas.clear();
        this.canvas.fill(Color.BLACK);

        this.canvas.drawRect(this.paddle1.x, this.paddle1.y, PADDLE_WIDTH * BLOCK_SIZE, PADDLE_HEIGHT * BLOCK_SIZE, Color.WHITE);
        this.canvas.drawRect(this.paddle2.x, this.paddle2.y, PADDLE_WIDTH * BLOCK_SIZE, PADDLE_HEIGHT * BLOCK_SIZE, Color.WHITE);

        for (int y = 0; y < BOARD_HEIGHT; y += 10) {
            this.canvas.drawRect(BOARD_WIDTH / 2 * BLOCK_SIZE - BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, 5 * BLOCK_SIZE, Color.WHITE);
        }

        this.canvas.drawDigit(
            BOARD_WIDTH / 4 - 2 * BLOCK_SIZE, BLOCK_SIZE,
            BOARD_WIDTH / 4 + 2 * BLOCK_SIZE, BLOCK_SIZE + 6 * BLOCK_SIZE,
            String.valueOf(this.scores[0]), Color.WHITE
        );
        this.canvas.drawDigit(
            3 * BOARD_WIDTH / 4 - 2 * BLOCK_SIZE, BLOCK_SIZE,
            3 * BOARD_WIDTH / 4 + 2 * BLOCK_SIZE, BLOCK_SIZE + 6 * BLOCK_SIZE,
            String.valueOf(this.scores[0]), Color.WHITE
        );

        this.canvas.show();
    }

    public void loop() {
        while (true) {
            update(0, 0);
            render();

            if (this.scores[0] >= WINNING_SCORE) {
                showWinner(1);
                break;
            } else if (this.scores[1] >= WINNING_SCORE) {
                showWinner(2);
                break;
            }

            try {
                Thread.sleep(1000 / 60);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }
    }

    public static void main(String[] args) {
        Pong pong = new Pong();

        pong.loop();
    }
}
