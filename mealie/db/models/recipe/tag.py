import sqlalchemy as sa
import sqlalchemy.orm as orm
from mealie.core import root_logger
from mealie.db.models._model_base import BaseMixins, SqlAlchemyBase
from slugify import slugify
from sqlalchemy.orm import validates

logger = root_logger.get_logger()

recipes2tags = sa.Table(
    "recipes2tags",
    SqlAlchemyBase.metadata,
    sa.Column("recipe_id", sa.Integer, sa.ForeignKey("recipes.id")),
    sa.Column("tag_id", sa.Integer, sa.ForeignKey("tags.id")),
)


class Tag(SqlAlchemyBase, BaseMixins):
    __tablename__ = "tags"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String, index=True, nullable=False)
    slug = sa.Column(sa.String, index=True, unique=True, nullable=False)
    recipes = orm.relationship("RecipeModel", secondary=recipes2tags, back_populates="tags")

    class Config:
        get_attr = "slug"

    @validates("name")
    def validate_name(self, key, name):
        assert name != ""
        return name

    def __init__(self, name, session=None) -> None:
        self.name = name.strip()
        self.slug = slugify(self.name)

    @classmethod
    def get_ref(cls, match_value: str, session=None):
        if not session or not match_value:
            return None

        slug = slugify(match_value)

        result = session.query(Tag).filter(Tag.slug == slug).one_or_none()
        if result:
            logger.debug("Category exists, associating recipe")
            return result
        else:
            logger.debug("Category doesn't exists, creating Category")
            return Tag(name=match_value)
