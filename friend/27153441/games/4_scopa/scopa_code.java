import java.util.Collections;
import java.util.ArrayList;
import java.util.List;
import java.util.Scanner;

public class Scopa {
    private static final String[] CARD_SUITS = {"Cups", "Coins", "Swords", "Clubs"};
    private static final int[] CARD_VALUES = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};

    private List<Player> players;
    private List<Card> deck;
    private List<Card> table;

    private static class Player {
        private String name;
        private int score;
        private List<Card> hand;
        private List<Card> discardPile;

        public Player(String name) {
            this.name = name;
            this.score = 0;
            this.hand = new ArrayList<>();
            this.discardPile = new ArrayList<>();
        }

        public Card turn() {
            Scanner scanner = new Scanner(System.in);

            System.out.print("Select a card to play: ");
            int cardIndex = scanner.nextInt();
            Card card = this.hand.remove(cardIndex);

            return card;
        }
    }

    private static class Card {
        private int value;
        private String suit;

        public Card(int value, String suit) {
            this.value = value;
            this.suit = suit;
        }
    }

    public Scopa(String player1Name, String player2Name, String player3Name) {
        this.players = new ArrayList<>();
        this.players.add(new Player(player1Name));
        this.players.add(new Player(player2Name));
        this.players.add(new Player(player3Name));
        Collections.shuffle(this.players);

        this.createShuffledDeck();

        for (Player player : this.players) {
            for (int i = 0; i < 3; i++) {
                Card card = this.deck.removeFirst();
                player.hand.add(card);
            }
        }

        this.table = new ArrayList<>();
        this.table.add(this.deck.removeFirst());
        this.table.add(this.deck.removeFirst());
        this.table.add(this.deck.removeFirst());
        this.table.add(this.deck.removeFirst());
    }

    private void createShuffledDeck() {
        this.deck = new ArrayList<>();

        for (String suit : CARD_SUITS) {
            for (int value : CARD_VALUES) {
                this.deck.add(new Card(value, suit));
            }
        }

        Collections.shuffle(this.deck);
    }

    private List<Card> getCardsWithValueSum(int value) {
        List<Card> cards = new ArrayList<>();
        int mostCards = 0;
        int masks = 1 << this.table.size();

        for (int i = 1; i < masks; i++) {
            List<Integer> subsetIndices = new ArrayList<>();

            for (int j = 0; j < this.table.size(); j++) {
                if ((i & (1 << j)) > 0) {
                    subsetIndices.add(j);
                }
            }

            if (subsetIndices.size() == 0) {
                continue;
            }

            int subsetSum = subsetIndices.stream()
                .map(index -> this.table.get(index).value)
                .reduce(0, Integer::sum);

            if (subsetSum == value && subsetIndices.size() > mostCards) {
                cards.clear();
                cards.addAll(subsetIndices.stream().map(index -> this.table.get(index)).toList());
                mostCards = subsetIndices.size();
            }
        }

        return cards;
    }

    private void assignPointsToPlayers() {
        Player playerWithMostCards = null;
        int mostCards = 0;
        Player playerWithMostCoinCards = null;
        int mostCoinCards = 0;
        Player playerWithSevenOfCoins = null;
        Player playerWithHighestSumOfCards = null;
        int highestSumOfCards = 0;

        for (Player player : this.players) {
            if (player.discardPile.size() > mostCards) {
                playerWithMostCards = player;
                mostCards = player.discardPile.size();
            }

            int coinCards = (int) player.discardPile.stream()
                .filter(card -> card.suit.equals("Coins"))
                .count();

            if (coinCards > mostCoinCards) {
                playerWithMostCoinCards = player;
                mostCoinCards = coinCards;
            }

            if (player.discardPile.stream().anyMatch(card -> card.value == 7 && card.suit.equals("Coins"))) {
                playerWithSevenOfCoins = player;
            }

            int sumOfCards = player.discardPile.stream()
                .map(card -> card.value)
                .reduce(0, Integer::sum);

            if (sumOfCards > highestSumOfCards) {
                playerWithHighestSumOfCards = player;
                highestSumOfCards = sumOfCards;
            }
        }

        playerWithMostCards.score += 1;
        playerWithMostCoinCards.score += 1;
        playerWithSevenOfCoins.score += 1;
        playerWithHighestSumOfCards.score += 1;
    }

    public boolean turn() {
        for (Player player : this.players) {
            System.out.println(player.name + "'s turn");

            int cardsOnTable = this.table.size();
            Card players_card = player.turn();
            List<Card> matchingCards = this.getCardsWithValueSum(players_card.value);

            if (matchingCards.size() > 0) {
                this.table.removeAll(matchingCards);
                player.discardPile.addAll(matchingCards);
            }
            
            if (player.hand.size() == 0) {
                int i = 0;

                while (this.deck.size() > 0 && i < 3) {
                    player.hand.add(this.deck.removeFirst());
                    i++;
                }

                if (this.deck.size() == 0) {
                    player.discardPile.addAll(this.table);
                    this.table.clear();

                    return true;
                }
            }

            if (this.table.size() == 0 && cardsOnTable > 0) {
                player.score += 1;
            }
        }

        return false;
    }

    public void play() {
        while (true) {
            boolean roundEnds = false;

            while(!roundEnds) {
                roundEnds = this.turn();
            }

            this.assignPointsToPlayers();

            for (Player player : this.players) {
                if (player.score >= 8) {
                    System.out.println(player.name + " wins!");
                    return;
                }
            }
        }
    }

    public static void main(String[] args) {
        Scopa scopa = new Scopa("Player 1", "Player 2", "Player 3");

        scopa.play();
    }
}
