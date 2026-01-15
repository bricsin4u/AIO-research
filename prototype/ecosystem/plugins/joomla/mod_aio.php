<?php
defined('_JEXEC') or die;

use Joomla\CMS\Factory;

// 1. Add Discovery Headers (Link tag)
$doc = Factory::getDocument();
$doc->addHeadLink(
    JUri::root() . 'index.php?option=com_ajax&module=aio&format=json&method=content',
    'alternate',
    'rel',
    ['type' => 'application/aio+json']
);

// Note: Joomla Modules are for display blocks. 
// For API endpoints, we usually use a Component or the com_ajax wrapper.
// This example assumes 'com_ajax' usage for lazy implementation, 
// OR a simpler 'System Plugin' is actually better for this than a module.
// But following the prompt for "lazy", we'll implement the helper logic here.

require_once __DIR__ . '/helper.php';
// Render nothing visual
?>
