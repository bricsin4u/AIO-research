<?php
defined('_JEXEC') or die;

use Joomla\CMS\Factory;

class ModAIOHelper
{
    public static function getContentAjax()
    {
        // Fetch latest articles
        $db = Factory::getDbo();
        $query = $db->getQuery(true)
            ->select($db->quoteName(array('id', 'title', 'introtext', 'fulltext', 'modified')))
            ->from($db->quoteName('#__content'))
            ->where($db->quoteName('state') . ' = 1')
            ->order($db->quoteName('modified') . ' DESC')
            ->setLimit(50);
            
        $db->setQuery($query);
        $articles = $db->loadObjectList();
        
        $chunks = [];
        $index = [];
        
        foreach ($articles as $curr) {
            $text = strip_tags($curr->introtext . $curr->fulltext);
            $clean_text = "# " . $curr->title . "\n\n" . $text;
            
            $id = 'article-' . $curr->id;
            
            $index[] = [
                'id' => $id,
                'path' => '/index.php?option=com_content&view=article&id=' . $curr->id, // Simplified path
                'title' => $curr->title,
                'modified' => $curr->modified,
                'token_estimate' => (int)(strlen($clean_text)/4)
            ];
            
            $chunks[] = [
                'id' => $id,
                'format' => 'markdown',
                'content' => $clean_text,
                'hash' => 'sha256:' . hash('sha256', $clean_text)
            ];
        }
        
        $data = [
            '$schema' => 'https://aio-standard.org/schema/v2.1/content.json',
            'aio_version' => '2.1',
            'generated' => date('c'),
            'index' => $index,
            'content' => $chunks
        ];

        echo json_encode($data);
        Factory::getApplication()->close();
    }
}
