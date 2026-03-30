from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from web.models import Flashcard, FlashcardDeck


class FlashcardModelTests(TestCase):
    """Test flashcard models."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

    def test_flashcard_deck_creation(self):
        """Test creating a flashcard deck."""
        deck = FlashcardDeck.objects.create(
            name="Test Deck", description="A test deck", creator=self.user, is_public=True
        )
        self.assertEqual(deck.name, "Test Deck")
        self.assertEqual(deck.creator, self.user)
        self.assertTrue(deck.is_public)
        self.assertEqual(deck.card_count, 0)

    def test_flashcard_deck_str(self):
        """Test the string representation of FlashcardDeck."""
        deck = FlashcardDeck.objects.create(name="Math Deck", creator=self.user)
        self.assertEqual(str(deck), "Math Deck")

    def test_flashcard_deck_slug_generation(self):
        """Test that slug is automatically generated."""
        deck = FlashcardDeck.objects.create(name="My Test Deck", creator=self.user)
        self.assertEqual(deck.slug, "my-test-deck")

    def test_flashcard_deck_unique_slug(self):
        """Test that duplicate deck names get unique slugs."""
        deck1 = FlashcardDeck.objects.create(name="Test Deck", creator=self.user)
        deck2 = FlashcardDeck.objects.create(name="Test Deck", creator=self.user)
        self.assertEqual(deck1.slug, "test-deck")
        self.assertEqual(deck2.slug, "test-deck-1")

    def test_flashcard_creation(self):
        """Test creating a flashcard."""
        deck = FlashcardDeck.objects.create(name="Test Deck", creator=self.user)
        card = Flashcard.objects.create(deck=deck, front_text="What is 2+2?", back_text="4", order=1)
        self.assertEqual(card.front_text, "What is 2+2?")
        self.assertEqual(card.back_text, "4")
        self.assertEqual(card.deck, deck)
        self.assertEqual(card.order, 1)

    def test_flashcard_str(self):
        """Test the string representation of Flashcard."""
        deck = FlashcardDeck.objects.create(name="Math Deck", creator=self.user)
        card = Flashcard.objects.create(deck=deck, front_text="Test", back_text="Answer", order=1)
        self.assertEqual(str(card), "Math Deck - Card 1")

    def test_flashcard_deck_card_count(self):
        """Test that card_count property works correctly."""
        deck = FlashcardDeck.objects.create(name="Test Deck", creator=self.user)
        self.assertEqual(deck.card_count, 0)

        # Add some cards
        Flashcard.objects.create(deck=deck, front_text="Q1", back_text="A1", order=1)
        Flashcard.objects.create(deck=deck, front_text="Q2", back_text="A2", order=2)

        # Refresh from database
        deck.refresh_from_db()
        self.assertEqual(deck.card_count, 2)


class FlashcardViewTests(TestCase):
    """Test flashcard views."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="testpass123"
        )

    def test_flashcard_deck_list_requires_login(self):
        """Test that deck list requires authentication."""
        response = self.client.get(reverse("flashcard_deck_list"))
        self.assertRedirects(response, "/en/accounts/login/?next=/en/flashcards/")

    def test_flashcard_deck_list_authenticated(self):
        """Test deck list view for authenticated user."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("flashcard_deck_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Flashcards")

    def test_create_flashcard_deck(self):
        """Test creating a new flashcard deck."""
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("flashcard_deck_create"), {"name": "Test Deck", "description": "A test deck", "is_public": "on"}
        )
        self.assertEqual(response.status_code, 302)

        deck = FlashcardDeck.objects.get(name="Test Deck")
        self.assertEqual(deck.creator, self.user)
        self.assertTrue(deck.is_public)

    def test_deck_detail_view(self):
        """Test viewing a deck detail."""
        deck = FlashcardDeck.objects.create(name="Test Deck", creator=self.user, is_public=True)

        self.client.force_login(self.user)
        response = self.client.get(reverse("flashcard_deck_detail", kwargs={"slug": deck.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Deck")

    def test_private_deck_access_denied(self):
        """Test that private decks are not accessible to other users."""
        deck = FlashcardDeck.objects.create(name="Private Deck", creator=self.user, is_public=False)

        self.client.force_login(self.other_user)
        response = self.client.get(reverse("flashcard_deck_detail", kwargs={"slug": deck.slug}))
        self.assertEqual(response.status_code, 302)

    def test_public_deck_accessible_to_all(self):
        """Test that public decks are accessible to all authenticated users."""
        deck = FlashcardDeck.objects.create(name="Public Deck", creator=self.user, is_public=True)

        self.client.force_login(self.other_user)
        response = self.client.get(reverse("flashcard_deck_detail", kwargs={"slug": deck.slug}))
        self.assertEqual(response.status_code, 200)

    def test_add_flashcard_to_deck(self):
        """Test adding a card to a deck."""
        deck = FlashcardDeck.objects.create(name="Test Deck", creator=self.user)

        self.client.force_login(self.user)
        response = self.client.post(
            reverse("flashcard_create", kwargs={"deck_slug": deck.slug}),
            {"front_text": "What is Python?", "back_text": "A programming language"},
        )
        self.assertEqual(response.status_code, 302)

        card = Flashcard.objects.get(deck=deck)
        self.assertEqual(card.front_text, "What is Python?")
        self.assertEqual(card.back_text, "A programming language")

    def test_study_mode_with_cards(self):
        """Test study mode when deck has cards."""
        deck = FlashcardDeck.objects.create(name="Study Deck", creator=self.user, is_public=True)
        Flashcard.objects.create(deck=deck, front_text="Question 1", back_text="Answer 1", order=1)

        self.client.force_login(self.user)
        response = self.client.get(reverse("flashcard_study", kwargs={"slug": deck.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Study: Study Deck")

    def test_study_mode_empty_deck_redirects(self):
        """Test that study mode redirects when deck is empty."""
        deck = FlashcardDeck.objects.create(name="Empty Deck", creator=self.user)

        self.client.force_login(self.user)
        response = self.client.get(reverse("flashcard_study", kwargs={"slug": deck.slug}))
        self.assertEqual(response.status_code, 302)

    def test_edit_deck_permission(self):
        """Test that only deck creator can edit deck."""
        deck = FlashcardDeck.objects.create(name="Test Deck", creator=self.user)

        # Owner can edit
        self.client.force_login(self.user)
        response = self.client.get(reverse("flashcard_deck_edit", kwargs={"slug": deck.slug}))
        self.assertEqual(response.status_code, 200)

        # Other user cannot edit
        self.client.force_login(self.other_user)
        response = self.client.get(reverse("flashcard_deck_edit", kwargs={"slug": deck.slug}))
        self.assertEqual(response.status_code, 404)

    def test_delete_deck_permission(self):
        """Test that only deck creator can delete deck."""
        deck = FlashcardDeck.objects.create(name="Test Deck", creator=self.user)

        # Other user cannot delete
        self.client.force_login(self.other_user)
        response = self.client.get(reverse("flashcard_deck_delete", kwargs={"slug": deck.slug}))
        self.assertEqual(response.status_code, 404)

        # Owner can delete
        self.client.force_login(self.user)
        response = self.client.post(reverse("flashcard_deck_delete", kwargs={"slug": deck.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(FlashcardDeck.objects.filter(id=deck.id).exists())
