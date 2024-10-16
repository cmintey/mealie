import random
from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from mealie.repos.repository_factory import AllRepositories
from mealie.schema.recipe.recipe import Recipe
from mealie.schema.user.user import UserRatingUpdate
from tests.utils import api_routes
from tests.utils.factories import random_bool, random_int, random_string
from tests.utils.fixture_schemas import TestUser


@pytest.fixture(scope="function")
def recipes(database: AllRepositories, user_tuple: tuple[TestUser, TestUser]) -> Generator[list[Recipe], None, None]:
    unique_user = random.choice(user_tuple)
    recipes_repo = database.recipes.by_group(UUID(unique_user.group_id))

    recipes: list[Recipe] = []
    for _ in range(random_int(10, 20)):
        slug = random_string()
        recipes.append(
            recipes_repo.create(
                Recipe(
                    user_id=unique_user.user_id,
                    group_id=unique_user.group_id,
                    name=slug,
                    slug=slug,
                )
            )
        )

    yield recipes
    for recipe in recipes:
        try:
            recipes_repo.delete(recipe.id, match_key="id")
        except Exception:
            pass


@pytest.mark.parametrize("use_self_route", [True, False])
def test_user_recipe_favorites(
    api_client: TestClient, user_tuple: tuple[TestUser, TestUser], recipes: list[Recipe], use_self_route: bool
):
    # we use two different users because pytest doesn't support function-scopes within parametrized tests
    if use_self_route:
        unique_user = user_tuple[0]
    else:
        unique_user = user_tuple[1]

    response = api_client.get(api_routes.users_id_favorites(unique_user.user_id), headers=unique_user.token)
    assert response.json()["ratings"] == []

    recipes_to_favorite = random.sample(recipes, random_int(5, len(recipes)))

    # add favorites
    for recipe in recipes_to_favorite:
        response = api_client.post(
            api_routes.users_id_favorites_slug(unique_user.user_id, recipe.slug), headers=unique_user.token
        )
        assert response.status_code == 200

    if use_self_route:
        get_url = api_routes.users_self_favorites
    else:
        get_url = api_routes.users_id_favorites(unique_user.user_id)

    response = api_client.get(get_url, headers=unique_user.token)
    ratings = response.json()["ratings"]

    assert len(ratings) == len(recipes_to_favorite)
    fetched_recipe_ids = {rating["recipeId"] for rating in ratings}
    favorited_recipe_ids = {str(recipe.id) for recipe in recipes_to_favorite}
    assert fetched_recipe_ids == favorited_recipe_ids

    # remove favorites
    recipe_favorites_to_remove = random.sample(recipes_to_favorite, 3)
    for recipe in recipe_favorites_to_remove:
        response = api_client.delete(
            api_routes.users_id_favorites_slug(unique_user.user_id, recipe.slug), headers=unique_user.token
        )
        assert response.status_code == 200

    response = api_client.get(get_url, headers=unique_user.token)
    ratings = response.json()["ratings"]

    assert len(ratings) == len(recipes_to_favorite) - len(recipe_favorites_to_remove)
    fetched_recipe_ids = {rating["recipeId"] for rating in ratings}
    removed_recipe_ids = {str(recipe.id) for recipe in recipe_favorites_to_remove}
    assert fetched_recipe_ids == favorited_recipe_ids - removed_recipe_ids


@pytest.mark.parametrize("add_favorite", [True, False])
def test_set_user_favorite_invalid_recipe_404(
    api_client: TestClient, user_tuple: tuple[TestUser, TestUser], add_favorite: bool
):
    unique_user = random.choice(user_tuple)
    if add_favorite:
        response = api_client.post(
            api_routes.users_id_favorites_slug(unique_user.user_id, random_string()), headers=unique_user.token
        )
    else:
        response = api_client.delete(
            api_routes.users_id_favorites_slug(unique_user.user_id, random_string()), headers=unique_user.token
        )
    assert response.status_code == 404


@pytest.mark.parametrize("use_self_route", [True, False])
def test_set_user_recipe_ratings(
    api_client: TestClient, user_tuple: tuple[TestUser, TestUser], recipes: list[Recipe], use_self_route: bool
):
    # we use two different users because pytest doesn't support function-scopes within parametrized tests
    if use_self_route:
        unique_user = user_tuple[0]
    else:
        unique_user = user_tuple[1]

    response = api_client.get(api_routes.users_id_ratings(unique_user.user_id), headers=unique_user.token)
    assert response.json()["ratings"] == []

    recipes_to_rate = random.sample(recipes, random_int(8, len(recipes)))

    expected_ratings_by_recipe_id: dict[str, UserRatingUpdate] = {}
    for recipe in recipes_to_rate:
        new_rating = UserRatingUpdate(
            rating=random.uniform(1, 5),
        )
        expected_ratings_by_recipe_id[str(recipe.id)] = new_rating
        response = api_client.post(
            api_routes.users_id_ratings_slug(unique_user.user_id, recipe.slug),
            json=new_rating.model_dump(),
            headers=unique_user.token,
        )
        assert response.status_code == 200

    if use_self_route:
        get_url = api_routes.users_self_ratings
    else:
        get_url = api_routes.users_id_ratings(unique_user.user_id)

    response = api_client.get(get_url, headers=unique_user.token)
    ratings = response.json()["ratings"]

    assert len(ratings) == len(recipes_to_rate)
    for rating in ratings:
        recipe_id = rating["recipeId"]
        assert rating["rating"] == expected_ratings_by_recipe_id[recipe_id].rating
        assert not rating["isFavorite"]


def test_set_user_rating_invalid_recipe_404(api_client: TestClient, user_tuple: tuple[TestUser, TestUser]):
    unique_user = random.choice(user_tuple)
    rating = UserRatingUpdate(rating=random.uniform(1, 5))
    response = api_client.post(
        api_routes.users_id_ratings_slug(unique_user.user_id, random_string()),
        json=rating.model_dump(),
        headers=unique_user.token,
    )
    assert response.status_code == 404


def test_set_rating_and_favorite(api_client: TestClient, user_tuple: tuple[TestUser, TestUser], recipes: list[Recipe]):
    unique_user = random.choice(user_tuple)
    recipe = random.choice(recipes)

    rating = UserRatingUpdate(rating=random.uniform(1, 5), is_favorite=True)
    response = api_client.post(
        api_routes.users_id_ratings_slug(unique_user.user_id, recipe.slug),
        json=rating.model_dump(),
        headers=unique_user.token,
    )
    assert response.status_code == 200

    response = api_client.get(api_routes.users_self_ratings_recipe_id(recipe.id), headers=unique_user.token)
    data = response.json()
    assert data["recipeId"] == str(recipe.id)
    assert data["rating"] == rating.rating
    assert data["isFavorite"] is True


@pytest.mark.parametrize("favorite_value", [True, False])
def test_set_rating_preserve_favorite(
    api_client: TestClient, user_tuple: tuple[TestUser, TestUser], recipes: list[Recipe], favorite_value: bool
):
    initial_rating_value = 1
    updated_rating_value = 5

    unique_user = random.choice(user_tuple)
    recipe = random.choice(recipes)
    rating = UserRatingUpdate(rating=initial_rating_value, is_favorite=favorite_value)
    response = api_client.post(
        api_routes.users_id_ratings_slug(unique_user.user_id, recipe.slug),
        json=rating.model_dump(),
        headers=unique_user.token,
    )
    assert response.status_code == 200

    response = api_client.get(api_routes.users_self_ratings_recipe_id(recipe.id), headers=unique_user.token)
    data = response.json()
    assert data["recipeId"] == str(recipe.id)
    assert data["rating"] == initial_rating_value
    assert data["isFavorite"] == favorite_value

    rating.rating = updated_rating_value
    rating.is_favorite = None  # this should be ignored and the favorite value should be preserved
    response = api_client.post(
        api_routes.users_id_ratings_slug(unique_user.user_id, recipe.slug),
        json=rating.model_dump(),
        headers=unique_user.token,
    )
    assert response.status_code == 200

    response = api_client.get(api_routes.users_self_ratings_recipe_id(recipe.id), headers=unique_user.token)
    data = response.json()
    assert data["recipeId"] == str(recipe.id)
    assert data["rating"] == updated_rating_value
    assert data["isFavorite"] == favorite_value


def test_set_favorite_preserve_rating(
    api_client: TestClient, user_tuple: tuple[TestUser, TestUser], recipes: list[Recipe]
):
    rating_value = random.uniform(1, 5)
    initial_favorite_value = random_bool()

    unique_user = random.choice(user_tuple)
    recipe = random.choice(recipes)
    rating = UserRatingUpdate(rating=rating_value, is_favorite=initial_favorite_value)
    response = api_client.post(
        api_routes.users_id_ratings_slug(unique_user.user_id, recipe.slug),
        json=rating.model_dump(),
        headers=unique_user.token,
    )
    assert response.status_code == 200

    response = api_client.get(api_routes.users_self_ratings_recipe_id(recipe.id), headers=unique_user.token)
    data = response.json()
    assert data["recipeId"] == str(recipe.id)
    assert data["rating"] == rating_value
    assert data["isFavorite"] is initial_favorite_value

    rating.is_favorite = not initial_favorite_value
    rating.rating = None  # this should be ignored and the rating value should be preserved
    response = api_client.post(
        api_routes.users_id_ratings_slug(unique_user.user_id, recipe.slug),
        json=rating.model_dump(),
        headers=unique_user.token,
    )
    assert response.status_code == 200

    response = api_client.get(api_routes.users_self_ratings_recipe_id(recipe.id), headers=unique_user.token)
    data = response.json()
    assert data["recipeId"] == str(recipe.id)
    assert data["rating"] == rating_value
    assert data["isFavorite"] is not initial_favorite_value


def test_set_rating_to_zero(api_client: TestClient, user_tuple: tuple[TestUser, TestUser], recipes: list[Recipe]):
    unique_user = random.choice(user_tuple)
    recipe = random.choice(recipes)

    rating_value = random.uniform(1, 5)
    rating = UserRatingUpdate(rating=rating_value)
    response = api_client.post(
        api_routes.users_id_ratings_slug(unique_user.user_id, recipe.slug),
        json=rating.model_dump(),
        headers=unique_user.token,
    )
    assert response.status_code == 200

    response = api_client.get(api_routes.users_self_ratings_recipe_id(recipe.id), headers=unique_user.token)
    data = response.json()
    assert data["rating"] == rating_value

    rating.rating = 0
    response = api_client.post(
        api_routes.users_id_ratings_slug(unique_user.user_id, recipe.slug),
        json=rating.model_dump(),
        headers=unique_user.token,
    )
    assert response.status_code == 200

    response = api_client.get(api_routes.users_self_ratings_recipe_id(recipe.id), headers=unique_user.token)
    data = response.json()
    assert data["rating"] == 0


def test_delete_recipe_deletes_ratings(
    database: AllRepositories, api_client: TestClient, user_tuple: tuple[TestUser, TestUser], recipes: list[Recipe]
):
    unique_user = random.choice(user_tuple)
    recipe = random.choice(recipes)
    rating = UserRatingUpdate(rating=random.uniform(1, 5), is_favorite=random.choice([True, False, None]))
    response = api_client.post(
        api_routes.users_id_ratings_slug(unique_user.user_id, recipe.slug),
        json=rating.model_dump(),
        headers=unique_user.token,
    )
    assert response.status_code == 200

    response = api_client.get(api_routes.users_self_ratings_recipe_id(recipe.id), headers=unique_user.token)
    assert response.status_code == 200
    assert response.json()

    database.recipes.delete(recipe.id, match_key="id")
    response = api_client.get(api_routes.users_self_ratings_recipe_id(recipe.id), headers=unique_user.token)
    assert response.status_code == 404


def test_recipe_rating_is_average_user_rating(
    api_client: TestClient, user_tuple: tuple[TestUser, TestUser], recipes: list[Recipe]
):
    recipe = random.choice(recipes)
    user_ratings = (UserRatingUpdate(rating=5), UserRatingUpdate(rating=2))

    for i, user in enumerate(user_tuple):
        response = api_client.post(
            api_routes.users_id_ratings_slug(user.user_id, recipe.slug),
            json=user_ratings[i].model_dump(),
            headers=user.token,
        )
        assert response.status_code == 200

    response = api_client.get(api_routes.recipes_slug(recipe.slug), headers=user_tuple[0].token)
    assert response.status_code == 200
    data = response.json()
    assert data["rating"] == 3.5


def test_recipe_rating_is_readonly(
    api_client: TestClient, user_tuple: tuple[TestUser, TestUser], recipes: list[Recipe]
):
    unique_user = random.choice(user_tuple)
    recipe = random.choice(recipes)

    rating = UserRatingUpdate(rating=random.uniform(1, 5), is_favorite=random.choice([True, False, None]))
    response = api_client.post(
        api_routes.users_id_ratings_slug(unique_user.user_id, recipe.slug),
        json=rating.model_dump(),
        headers=unique_user.token,
    )
    assert response.status_code == 200

    response = api_client.get(api_routes.recipes_slug(recipe.slug), headers=unique_user.token)
    assert response.status_code == 200
    data = response.json()
    assert data["rating"] == rating.rating

    # try to update the rating manually and verify it didn't change
    new_rating = random.uniform(1, 5)
    assert new_rating != rating.rating
    response = api_client.patch(
        api_routes.recipes_slug(recipe.slug), json={"rating": new_rating}, headers=unique_user.token
    )
    assert response.status_code == 200
    assert response.json()["rating"] == rating.rating

    response = api_client.get(api_routes.recipes_slug(recipe.slug), headers=unique_user.token)
    assert response.status_code == 200
    data = response.json()
    assert data["rating"] == rating.rating
