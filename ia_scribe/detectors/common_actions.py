# Page type assertions
A_ASSERT_CHAPTER = 'assert_chapter'
A_ASSERT_NORMAL = 'assert_normal'
A_ASSERT_TITLE = 'assert_title'
A_ASSERT_COPYRIGHT = 'assert_copyright'
A_ASSERT_COVER = 'assert_cover'
A_ASSERT_CONTENTS = 'assert_contents'
A_ASSERT_WHITE_CARD = 'assert_white_card'
A_ASSERT_FOLDOUT = 'assert_foldout'
A_ASSERT_COLOR_CARD = 'assert_color_card'
A_ASSERT_INDEX = 'assert_index'
A_ASSERT_TISSUE = 'assert_tissue'

A_PAGE_TYPE_ASSERTIONS = {
    A_ASSERT_CHAPTER, A_ASSERT_NORMAL, A_ASSERT_TITLE, A_ASSERT_COPYRIGHT,
    A_ASSERT_COVER, A_ASSERT_CONTENTS, A_ASSERT_WHITE_CARD, A_ASSERT_FOLDOUT,
    A_ASSERT_COLOR_CARD, A_ASSERT_INDEX, A_ASSERT_TISSUE
}

# TODO: Move this dict somewhere more appropriate
ASSERT_ACTIONS_TO_PAGE_TYPE = {
    A_ASSERT_CHAPTER: 'Chapter',
    A_ASSERT_NORMAL: 'Normal',
    A_ASSERT_TITLE: 'Title',
    A_ASSERT_COPYRIGHT: 'Copyright',
    A_ASSERT_COVER: 'Cover',
    A_ASSERT_CONTENTS: 'Contents',
    A_ASSERT_WHITE_CARD: 'White Card',
    A_ASSERT_FOLDOUT: 'Foldout',
    A_ASSERT_COLOR_CARD: 'Color Card',
    A_ASSERT_INDEX: 'Index',
    A_ASSERT_TISSUE: 'Tissue'
}
