from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sql_structure


class DataBase:
    def __init__(self, db_url):
        engine = create_engine(db_url)
        sql_structure.Base.metadata.create_all(bind=engine)
        self.session_m = sessionmaker(bind=engine)

    @staticmethod
    def __get_or_create(session, model, **data):
        db_model = session.query(model).filter(model.url == data['url']).first()
        if not db_model:
            db_model = model(**data)

        return db_model

    def create_post(self, data):
        session = self.session_m()
        tags = map(lambda tag_data: self.__get_or_create(session, sql_structure.Tag, **tag_data), data['tags'])
        writer = self.__get_or_create(session, sql_structure.Writer, **data['writer'])
        post = self.__get_or_create(session, sql_structure.Post, **data['post_data'], writer=writer)
        post.tags.extend(tags)
        session.add(post)
        try:
            session.commit()
        except Exception as e:
            session.rollback()
        finally:
            session.close()
