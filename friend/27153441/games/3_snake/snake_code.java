import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public class Snake {
    private static final int BLOCK_SIZE = 5;

    private static enum Direction {
        UP,
        DOWN,
        LEFT,
        RIGHT
    }

    private static class Block {
        private int x;
        private int y;

        public Block(int x, int y) {
            this.x = x;
            this.y = y;
        }
    }

    private int board_size;
    private List<Block> snake_blocks;
    private Direction direction;
    private Block food_block;

    public Snake(int board_size) {
        Random random = new Random();

        this.board_size = board_size;
        this.snake_blocks = new ArrayList<>();
        this.snake_blocks.add(new Block(0, board_size));
        this.direction = Direction.UP;
        this.food_block = new Block(random.nextInt(board_size), random.nextInt(board_size));
    }

    private void moveSnake(boolean addBlock) {
        Block head = snake_blocks.get(0);

        if (direction == Direction.UP) {
            snake_blocks.add(0, new Block(head.x, head.y - 1));
        } else if (direction == Direction.DOWN) {
            snake_blocks.add(0, new Block(head.x, head.y + 1));
        } else if (direction == Direction.LEFT) {
            snake_blocks.add(0, new Block(head.x - 1, head.y));
        } else if (direction == Direction.RIGHT) {
            snake_blocks.add(0, new Block(head.x + 1, head.y));
        }

        if (!addBlock) {
            snake_blocks.remove(snake_blocks.size() - 1);
        }
    }

    private boolean snakeOnFood() {
        Block head = snake_blocks.get(0);

        return head.x == food_block.x && head.y == food_block.y;
    }

    private boolean snakeTouchesItself() {
        Block head = snake_blocks.get(0);

        for (int i = 1; i < snake_blocks.size(); i++) {
            Block block = snake_blocks.get(i);

            if (head.x == block.x && head.y == block.y) {
                return true;
            }
        }

        return false;
    }

    private void drawBoard() {
        Graphics.clear();

        for (Block block : snake_blocks) {
            Graphics.draw(block.x * BLOCK_SIZE, block.y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE, Color.GREEN);
        }

        Graphics.draw(food_block.x * BLOCK_SIZE, food_block.y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE, Color.RED);
    }

    private boolean boardIsFull() {
        for (int x = 0; x < this.board_size; x++) {
            for (int y = 0; y < this.board_size; y++) {
                if (this.snake_blocks.stream().filter(block -> block.x == x && block.y == y).findAny().isEmpty()) {
                    return false;
                }
            }
        }

        return true;
    }

    private boolean loop() {
        Random random = new Random();

        while (true) {
            boolean addBlock = false;

            drawBoard();

            KeyboardKey key = KeyboardInterface.lastKeyPressed();

            if (key == KeyboardKey.UP) {
                direction = Direction.UP;
            } else if (key == KeyboardKey.DOWN) {
                direction = Direction.DOWN;
            } else if (key == KeyboardKey.LEFT) {
                direction = Direction.LEFT;
            } else if (key == KeyboardKey.RIGHT) {
                direction = Direction.RIGHT;
            }

            if (snakeOnFood()) {
                addBlock = true;
                food_block = new Block(random.nextInt(board_size), random.nextInt(board_size));
            }

            if (snakeTouchesItself()) {
                return false;
            }

            if (boardIsFull()) {
                return true;
            }

            moveSnake(addBlock);
        }
    }

    public static void main(String[] args) {
        Snake snake = new Snake(Integer.parseInt(args[0]));

        snake.loop();
    }
}
